import re, sys, time
import peewee as pw
import playhouse.migrate


try:
  UNICODE_EXISTS = bool(type(unicode))
except NameError:
  unicode = lambda s: str(s)



def calc_table_changes(existing_tables):
  existing_tables = set(existing_tables)
  table_names_to_models = {cls._meta.db_table:cls for cls in all_models.keys()}
  defined_tables = set(table_names_to_models.keys())
  adds = defined_tables - existing_tables
  deletes = existing_tables - defined_tables
  renames = {}
  for to_add in list(adds):
    cls = table_names_to_models[to_add]
    if hasattr(cls._meta, 'aka'):
      akas = cls._meta.aka
      if hasattr(akas, 'lower'):
        akas = [akas]
      for a in akas:
        if a in deletes:
          renames[a] = to_add
          adds.remove(to_add)
          deletes.remove(a)
          break
  return adds, deletes, renames

def auto_detect_migrator(db):
  if db.__class__.__name__ in ['PostgresqlDatabase']:
    return playhouse.migrate.PostgresqlMigrator(db)
  if db.__class__.__name__ in ['SqliteDatabase']:
    return playhouse.migrate.SqliteMigrator(db)
  raise Exception("could not auto-detect migrator for %s - please provide one via the migrator kwarg" % repr(db.__class__.__name__))

_re_varchar = re.compile('^varchar[(]\\d+[)]$')
def normalize_column_type(t):
  t = t.lower()
  if t in ['serial']: t = 'integer'
  if t in ['character varying']: t = 'varchar'
  if t in ['timestamp without time zone']: t = 'timestamp'
  if t in ['double precision']: t = 'real'
  if _re_varchar.match(t): t = 'varchar'
  return unicode(t)
  
def normalize_field_type(field):
  t = field.get_column_type()
  return normalize_column_type(t)
  
def can_convert(type1, type2):
  return True
  
def column_def_changed(a, b):
  return a.null!=b.null or a.data_type!=b.data_type or a.primary_key!=b.primary_key

def calc_column_changes(migrator, qc, ntn, existing_columns, defined_fields):
  defined_fields_by_column_name = {unicode(f.db_column):f for f in defined_fields}
  existing_columns = [pw.ColumnMetadata(c.name, normalize_column_type(c.data_type), c.null, c.primary_key, c.table) for c in existing_columns]
  defined_columns = [pw.ColumnMetadata(
    unicode(f.db_column),
    normalize_field_type(f),
    f.null,
    f.primary_key,
    unicode(ntn)
  ) for f in defined_fields if isinstance(f, pw.Field)]
  
  existing_cols_by_name = {c.name:c for c in existing_columns}
  defined_cols_by_name = {c.name:c for c in defined_columns}
  existing_col_names = set(existing_cols_by_name.keys())
  defined_col_names = set(defined_cols_by_name.keys())
  new_cols = defined_col_names - existing_col_names
  delete_cols = existing_col_names - defined_col_names
  rename_cols = {}
  for cn in list(new_cols):
    sc = defined_cols_by_name[cn]
    field = defined_fields_by_column_name[cn]
    if hasattr(field, 'akas'):
      for aka in field.akas:
        if aka in delete_cols:
          ec = existing_cols_by_name[aka]
          if can_convert(sc.data_type, ec.data_type):
            rename_cols[ec.name] = sc.name
            new_cols.discard(cn)
            delete_cols.discard(aka)
  
  alter_statements = []
  renames_new_to_old = {v:k for k,v in rename_cols.items()}
  for col_name in defined_col_names - new_cols:
    existing_col = existing_cols_by_name[renames_new_to_old.get(col_name, col_name)]
    defined_col = defined_cols_by_name[col_name]
    if column_def_changed(existing_col, defined_col):
      len_alter_statements = len(alter_statements)
      if existing_col.null and not defined_col.null:
        op = migrator.add_not_null(ntn, defined_col.name, generate=True)
        alter_statements.append(qc.parse_node(op))
      if not existing_col.null and defined_col.null:
        op = migrator.drop_not_null(ntn, defined_col.name, generate=True)
        alter_statements.append(qc.parse_node(op))
      if not (len_alter_statements < len(alter_statements)):
        raise Exception("i don't know how to change %s into %s" % (existing_col, defined_col))
        

  return new_cols, delete_cols, rename_cols, alter_statements

def calc_changes(db):
  migrator = None # expose eventually?
  if migrator is None:
    migrator = auto_detect_migrator(db)
    
  existing_tables = db.get_tables()
  existing_columns = {table:db.get_columns(table) for table in existing_tables}
  existing_indexes = {table:db.get_indexes(table) for table in existing_tables}

  table_names_to_models = {cls._meta.db_table:cls for cls in all_models.keys()}

  qc = db.compiler()
  to_run = []

  table_adds, table_deletes, table_renames = calc_table_changes(existing_tables)
  to_run += [qc.create_table(table_names_to_models[tbl]) for tbl in table_adds]
  for k,v in table_renames.items():
    ops = migrator.rename_table(k,v, generate=True)
    if not hasattr(ops, '__iter__'): ops = [ops] # sometimes pw return arrays, sometimes not
    to_run += [qc.parse_node(op) for op in ops]


  rename_cols_by_table = {}
  for etn, ecols in existing_columns.items():
    if etn in table_deletes: continue
    ntn = table_renames.get(etn, etn)
    dcols = table_names_to_models[ntn]._meta.sorted_fields
    defined_column_name_to_field = {unicode(f.db_column):f for f in dcols}
    adds, deletes, renames, alter_statements = calc_column_changes(migrator, qc, ntn, ecols, dcols)
    for column_name in adds:
      operation = migrator.alter_add_column(ntn, column_name, defined_column_name_to_field[column_name], generate=True)
      to_run.append(qc.parse_node(operation))
    for column_name in deletes:
      operation = migrator.drop_column(ntn, column_name, generate=True, cascade=False)
      to_run.append(qc.parse_node(operation))
    for ocn, ncn in renames.items():
      operation = migrator.rename_column(ntn, ocn, ncn, generate=True)
      to_run.append(qc.parse_node(operation))
    to_run += alter_statements
    rename_cols_by_table[ntn] = renames
  
  '''
  to_run += calc_index_changes(existing_indexes, $schema_indexes, renames, rename_cols_by_table)

  to_run += calc_fk_changes($foreign_keys, Set.new(existing_tables.keys), renames)

  to_run += calc_perms_changes($schema_tables, noop) unless $check_perms_for.empty?

  to_run += sql_drops(deletes)
  '''

  
  
  to_run += [qc.parse_node(pw.Clause(pw.SQL('DROP TABLE'), pw.Entity(tbl))) for tbl in table_deletes]
  return to_run
  
def evolve(db, interactive=True):
  to_run = calc_changes(db)
  if not to_run:
    if interactive:
      print 'your database is up to date!'
    return
  
  if interactive:
    _confirm(db, to_run)

  _execute(db, to_run, interactive=interactive)


def _execute(db, to_run, interactive=True):
  if interactive: print
  with db.atomic() as txn:
    for sql, params in to_run:
      if interactive: print ' ', sql, params
      db.execute_sql(sql, params)
  if interactive:
    print
    print 'SUCCESS!'
    print 'https://github.com/keredson/peewee-db-evolve'
    print

def _confirm(db, to_run):
  print
  print '------------------'
  print ' peewee-db-evolve'
  print '------------------'
  print
  print "Your database needs the following %s:" % ('changes' if len(to_run)>1 else 'change')
  print 
  for sql, params in to_run:
    print '  %s;' % sql
  print 
  while True:
    print 'Do you want to run %s? (type yes or no)' % ('these commands' if len(to_run)>1 else 'this command'),
    response = raw_input().strip().lower()
    if response=='yes':
      break
    if response=='no':
      sys.exit(1)
  print 'Running in',
  for i in range(3):
    print '%i...' % (3-i),
    time.sleep(1)
  print
  



all_models = {}

def register(model):
  all_models[model] = []

def clear():
  all_models.clear()

def _add_model_hook():
  init = pw.BaseModel.__init__
  def _init(*args, **kwargs):
    cls = args[0]
    fields = args[3]
    if '__module__' in fields:
      del fields['__module__']
    register(cls)
    init(*args, **kwargs)
  pw.BaseModel.__init__ = _init
_add_model_hook()

def _add_field_hook():
  init = pw.Field.__init__
  def _init(*args, **kwargs):
    self = args[0]
    if 'aka' in kwargs:
      akas = kwargs['aka']
      if hasattr(akas, 'lower'):
        akas = [akas]
      self.akas = akas
      del kwargs['aka']
    init(*args, **kwargs)
  pw.Field.__init__ = _init
_add_field_hook()


def add_evolve():
  pw.Database.evolve = evolve
add_evolve()


__all__ = ['evolve']

