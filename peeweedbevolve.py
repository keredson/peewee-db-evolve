from __future__ import print_function

import collections, re, sys, time
import peewee as pw
import playhouse.migrate


DEBUG = False

__version__ = '0.2.1'


try:
  UNICODE_EXISTS = bool(type(unicode))
except NameError:
  unicode = lambda s: str(s)


def sort_by_fk_deps(table_names):
  table_names_to_models = {cls._meta.db_table:cls for cls in all_models.keys() if cls._meta.db_table in table_names}
  models = pw.sort_models_topologically(table_names_to_models.values())
  return [model._meta.db_table for model in models]
  
def calc_table_changes(existing_tables):
  existing_tables = set(existing_tables)
  table_names_to_models = {unicode(cls._meta.db_table):cls for cls in all_models.keys()}
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
        a = unicode(a)
        if a in deletes:
          renames[a] = to_add
          adds.remove(to_add)
          deletes.remove(a)
          break
  adds = sort_by_fk_deps(adds)
  return adds, deletes, renames
  
def is_postgres(db):
  return db.__class__.__name__ in ['PostgresqlDatabase','PooledPostgresqlDatabase']

def is_mysql(db):
  return db.__class__.__name__ in ['MySQLDatabase']

def is_sqlite(db):
  return db.__class__.__name__ in ['SqliteDatabase']

def auto_detect_migrator(db):
  if is_postgres(db):
    return playhouse.migrate.PostgresqlMigrator(db)
  if is_sqlite(db):
    return playhouse.migrate.SqliteMigrator(db)
  if is_mysql(db):
    return playhouse.migrate.MySQLMigrator(db)
  raise Exception("could not auto-detect migrator for %s - please provide one via the migrator kwarg" % repr(db.__class__.__name__))

_re_varchar = re.compile('^varchar[(]\\d+[)]$')
def normalize_column_type(t):
  t = t.lower()
  if t in ['serial','primary_key','int']: t = 'integer'
  if t in ['character varying','varchar']: t = 'string'
  if t in ['timestamp', 'timestamp with time zone', 'timestamp without time zone']: t = 'datetime'
  if t in ['double precision','numeric','decimal']: t = 'float'
  if t in ['bool']: t = 'boolean'
  if _re_varchar.match(t): t = 'string'
  return unicode(t)
  
def normalize_field_type(field):
#  t = field.get_column_type()
  t = field.db_field
  return normalize_column_type(t)
  
def can_convert(type1, type2):
  return True
  
def column_def_changed(a, b):
  return a.null!=b.null or a.data_type!=b.data_type or a.primary_key!=b.primary_key

ForeignKeyMetadata = collections.namedtuple('ForeignKeyMetadata', ('column', 'dest_table', 'dest_column', 'table', 'name'))
    
def get_foreign_keys_by_table(db, schema='public'):
  fks_by_table = collections.defaultdict(list)
  if is_postgres(db):
    sql = """
      select kcu.column_name, ccu.table_name, ccu.column_name, tc.table_name, tc.constraint_name
      from information_schema.table_constraints as tc
      join information_schema.key_column_usage as kcu
        on (tc.constraint_name = kcu.constraint_name and tc.constraint_schema = kcu.constraint_schema)
      join information_schema.constraint_column_usage as ccu
        on (ccu.constraint_name = tc.constraint_name and ccu.constraint_schema = tc.constraint_schema)
      where tc.constraint_type = 'FOREIGN KEY' and tc.table_schema = %s
    """
    cursor = db.execute_sql(sql, (schema,))
  elif is_mysql(db):
    sql = """
      select column_name, referenced_table_name, referenced_column_name, table_name, constraint_name
      from information_schema.key_column_usage
      where table_schema=database() and referenced_table_name is not null and referenced_column_name is not null
    """
    cursor = db.execute_sql(sql, [])
  elif is_sqlite(db):
    # does not work
    sql = """
      SELECT sql
        FROM (
              SELECT sql sql, type type, tbl_name tbl_name, name name
                FROM sqlite_master
               UNION ALL
              SELECT sql, type, tbl_name, name
                FROM sqlite_temp_master
             )
       WHERE type != 'meta'
         AND sql NOTNULL
         AND name NOT LIKE 'sqlite_%'
         AND sql LIKE '%REFERENCES%'
       ORDER BY substr(type, 2, 1), name
    """
    cursor = db.execute_sql(sql, [])
  else:
    raise Exception("don't know how to get FKs for %s" % db)
  for row in cursor.fetchall():
    fk = ForeignKeyMetadata(row[0], row[1], row[2], row[3], row[4])
    fks_by_table[fk.table].append(fk)
  return fks_by_table

def calc_column_changes(db, migrator, etn, ntn, existing_columns, defined_fields, existing_fks):
  qc = db.compiler()
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
  not_new_columns = defined_col_names - new_cols
  
  # look for column metadata changes
  for col_name in not_new_columns:
    existing_col = existing_cols_by_name[renames_new_to_old.get(col_name, col_name)]
    defined_col = defined_cols_by_name[col_name]
    if column_def_changed(existing_col, defined_col):
      len_alter_statements = len(alter_statements)
      if existing_col.null and not defined_col.null:
        field = defined_fields_by_column_name[defined_col.name]
        alter_statements += add_not_null(db, migrator, ntn, field, defined_col.name)
      if not existing_col.null and defined_col.null:
        op = migrator.drop_not_null(ntn, defined_col.name, generate=True)
        alter_statements.append(qc.parse_node(op))
      if not (len_alter_statements < len(alter_statements)):
        if existing_col.data_type == u'array':
          # type reporting for arrays is broken in peewee
          # it returns the underlying type of the array, not array
          # ignore array columns for now (HACK)
          pass
        else:
          raise Exception("In table %s don't know how to change %s into %s" % (repr(ntn), existing_col, defined_col))
  
  # look for fk changes
  existing_fks_by_column = {fk.column:fk for fk in existing_fks}
  for col_name in not_new_columns:
    existing_column_name = renames_new_to_old.get(col_name, col_name)
    defined_field = defined_fields_by_column_name[col_name]
    existing_fk = existing_fks_by_column.get(existing_column_name)
    if isinstance(defined_field, pw.ForeignKeyField) and not existing_fk and not (hasattr(defined_field,'fake') and defined_field.fake):
      op = qc._create_foreign_key(defined_field.model_class, defined_field)
      alter_statements.append(qc.parse_node(op))
    if not isinstance(defined_field, pw.ForeignKeyField) and existing_fk:
      alter_statements += drop_foreign_key(db, migrator, ntn, existing_fk.name)
        

  return new_cols, delete_cols, rename_cols, alter_statements

def drop_foreign_key(db, migrator, table_name, fk_name):
  drop_stmt = 'drop foreign key' if is_mysql(db) else 'DROP CONSTRAINT'
  op = pw.Clause(pw.SQL('ALTER TABLE'), pw.Entity(table_name), pw.SQL(drop_stmt), pw.Entity(fk_name))
  return normalize_whatever_junk_peewee_migrations_gives_you(db, migrator, op)

def alter_add_column(db, migrator, ntn, column_name, field):
  qc = db.compiler()
  operation = migrator.alter_add_column(ntn, column_name, field, generate=True)
  to_run = [qc.parse_node(operation)]
  if is_mysql(db) and isinstance(field, pw.ForeignKeyField):
    op = qc._create_foreign_key(field.model_class, field)
    to_run.append(qc.parse_node(op))
  return to_run

def calc_changes(db):
  migrator = None # expose eventually?
  if migrator is None:
    migrator = auto_detect_migrator(db)
    
  existing_tables = [unicode(t) for t in db.get_tables()]
  existing_columns = {table:db.get_columns(table) for table in existing_tables}
  existing_indexes = {table:db.get_indexes(table) for table in existing_tables}
  foreign_keys_by_table = get_foreign_keys_by_table(db)

  table_names_to_models = {cls._meta.db_table:cls for cls in all_models.keys()}

  qc = db.compiler()
  to_run = []

  table_adds, table_deletes, table_renames = calc_table_changes(existing_tables)
  table_renamed_from = {v:k for k,v in table_renames.items()}
  to_run += [qc.create_table(table_names_to_models[tbl]) for tbl in table_adds]
  for k,v in table_renames.items():
    ops = migrator.rename_table(k,v, generate=True)
    if not hasattr(ops, '__iter__'): ops = [ops] # sometimes pw return arrays, sometimes not
    to_run += [qc.parse_node(op) for op in ops]


  rename_cols_by_table = {}
  deleted_cols_by_table = {}
  for etn, ecols in existing_columns.items():
    if etn in table_deletes: continue
    ntn = table_renames.get(etn, etn)
    defined_fields = table_names_to_models[ntn]._meta.sorted_fields
    defined_column_name_to_field = {unicode(f.db_column):f for f in defined_fields}
    adds, deletes, renames, alter_statements = calc_column_changes(db, migrator, etn, ntn, ecols, defined_fields, foreign_keys_by_table[etn])
    for column_name in adds:
      field = defined_column_name_to_field[column_name]
      to_run += alter_add_column(db, migrator, ntn, column_name, field)
      if not field.null:
        # alter_add_column strips null constraints
        # add them back after setting any defaults
        if field.default:
          operation = migrator.apply_default(ntn, column_name, field, generate=True)
          to_run.append(qc.parse_node(operation))
        else:
          to_run.append(('-- adding a not null column without a default will fail if the table is not empty',[]))
        to_run += add_not_null(db, migrator, ntn, field, column_name)
          
    for column_name in deletes:
      to_run += drop_column(db, migrator, ntn, column_name)
    for ocn, ncn in renames.items():
      field = defined_column_name_to_field[ncn]
      to_run += rename_column(db, migrator, ntn, ocn, ncn, field)
    to_run += alter_statements
    rename_cols_by_table[ntn] = renames
    deleted_cols_by_table[ntn] = deletes
  
  for ntn, model in table_names_to_models.items():
    etn = table_renamed_from.get(ntn, ntn)
    deletes = deleted_cols_by_table.get(ntn,set())
    existing_indexes_for_table = [i for i in existing_indexes.get(etn, []) if not any([(c in deletes) for c in i.columns])]
    to_run += calc_index_changes(db, migrator, existing_indexes_for_table, model, rename_cols_by_table.get(ntn, {}))
  
  '''
  to_run += calc_index_changes(existing_indexes, $schema_indexes, renames, rename_cols_by_table)

  to_run += calc_perms_changes($schema_tables, noop) unless $check_perms_for.empty?

  '''

  
  
  to_run += [qc.parse_node(pw.Clause(pw.SQL('DROP TABLE'), pw.Entity(tbl))) for tbl in table_deletes]
  return to_run

def rename_column(db, migrator, ntn, ocn, ncn, field):
  qc = db.compiler()
  if is_mysql(db):
    junk = pw.Clause(
      pw.SQL('ALTER TABLE'), pw.Entity(ntn), pw.SQL('CHANGE'), pw.Entity(ocn), qc.field_definition(field)
    )
  else:
    junk = migrator.rename_column(ntn, ocn, ncn, generate=True)
  return normalize_whatever_junk_peewee_migrations_gives_you(db, migrator, junk)

def normalize_op_to_clause(db, migrator, op):
  if isinstance(op, pw.Clause): return op
  playhouse.migrate
  kwargs = op.kwargs.copy()
  kwargs['generate'] = True
  ret = getattr(migrator, op.method)(*op.args, **kwargs)
  return ret

def normalize_whatever_junk_peewee_migrations_gives_you(db, migrator, junk):
  # sometimes a clause, sometimes an operation, sometimes a list mixed with clauses and operations
  # turn it into a list of (sql,params) tuples
  if not hasattr(junk, '__iter__'):
    junk = [junk]
  junk = [normalize_op_to_clause(db, migrator, o) for o in junk]
  qc = db.compiler()
  junk = [qc.parse_node(clause) for clause in junk]
  return junk

def drop_column(db, migrator, ntn, column_name):
  return normalize_whatever_junk_peewee_migrations_gives_you(db, migrator, migrator.drop_column(ntn, column_name, generate=True, cascade=False))
  
def add_not_null(db, migrator, table, field, column_name):
  qc = db.compiler()
  if is_postgres(db) or is_sqlite(db):
    junk = migrator.add_not_null(table, column_name, generate=True)
    return normalize_whatever_junk_peewee_migrations_gives_you(db, migrator, junk)
  elif is_mysql(db):
    op = pw.Clause(pw.SQL('ALTER TABLE'), pw.Entity(table), pw.SQL('MODIFY'), qc.field_definition(field))
    return [qc.parse_node(op)]
  raise Exception('how do i add a not null for %s?' % db)

def indexes_are_same(i1, i2):
  return unicode(i1.table)==unicode(i2.table) and i1.columns==i2.columns and i1.unique==i2.unique

def normalize_indexes(indexes):
  return [(unicode(idx.table), tuple(sorted([unicode(c) for c in idx.columns])), idx.unique) for idx in indexes]

  
def calc_index_changes(db, migrator, existing_indexes, model, renamed_cols):
  qc = db.compiler()  
  to_run = []
  fields = list(model._meta.sorted_fields)
  fields_by_column_name = {f.db_column:f for f in fields}
  pk_cols = set([unicode(f.db_column) for f in fields if f.primary_key])
  existing_indexes = [i for i in existing_indexes if not all([(unicode(c) in pk_cols) for c in i.columns])]
  normalized_existing_indexes = normalize_indexes(existing_indexes)
  existing_indexes_by_normalized_existing_indexes = dict(zip(normalized_existing_indexes, existing_indexes))
  normalized_existing_indexes = set(normalized_existing_indexes)
  defined_indexes = [pw.IndexMetadata('', '', [f.db_column], f.unique, model._meta.db_table) for f in model._fields_to_index()]
  for fields, unique in model._meta.indexes:
    try:
      columns = [model._meta.fields[fname].db_column for fname in fields]
    except KeyError as e:
      raise Exception("Index %s on %s references field %s in a multi-column index, but that field doesn't exist. (Be sure to use the field name, not the db_column name, when specifying a multi-column index.)" % ((fields, unique), model.__name__, repr(e.message)))
    defined_indexes.append(pw.IndexMetadata('', '', columns, unique, model._meta.db_table))
  normalized_defined_indexes = set(normalize_indexes(defined_indexes))
  to_add = normalized_defined_indexes - normalized_existing_indexes
  to_del = normalized_existing_indexes - normalized_defined_indexes
  for index in to_add:
    to_run.append(qc.create_index(model, [fields_by_column_name[col] for col in index[1]], index[2]))
  for index in to_del:
    index = existing_indexes_by_normalized_existing_indexes[index]
    op = migrator.drop_index(model._meta.db_table, index.name, generate=True)
    to_run.append(qc.parse_node(op))
  return to_run
  
def evolve(db, interactive=True):
  to_run = calc_changes(db)
  if not to_run:
    if interactive:
      print()
      print('Nothing to do... Your database is up to date!')
      print('https://github.com/keredson/peewee-db-evolve')
      print()
    return
  
  commit = True
  if interactive:
    commit = _confirm(db, to_run)

  _execute(db, to_run, interactive=interactive, commit=commit)


def _execute(db, to_run, interactive=True, commit=True):
  if interactive: print()
  try:
    with db.atomic() as txn:
      for sql, params in to_run:
        if interactive or DEBUG: print(' ', sql, params)
        if sql.strip().startswith('--'): continue
        db.execute_sql(sql, params)
      if interactive:
        print()
        print('SUCCESS!' if commit else 'TEST PASSED - ROLLING BACK')
        print('https://github.com/keredson/peewee-db-evolve')
        print()
      if not commit:
        txn.rollback()
  except Exception as e:
    print()
    print('------------------------------------------')
    print(' SQL EXCEPTION - ROLLING BACK ALL CHANGES')
    print('------------------------------------------')
    print()
    raise e

def _confirm(db, to_run):
  print()
  print('------------------')
  print(' peewee-db-evolve')
  print('------------------')
  print()
  print("Your database needs the following %s:" % ('changes' if len(to_run)>1 else 'change'))
  print()
  print('  BEGIN TRANSACTION;\n')
  for sql, params in to_run:
    print('  %s;' % sql)
  print('\n  COMMIT;')
  print()
  while True:
    print('Do you want to run %s? (type yes, no or test)' % ('these commands' if len(to_run)>1 else 'this command'), end=' ')
    response = raw_input().strip().lower()
    if response=='yes' or response=='test':
      break
    if response=='no':
      sys.exit(1)
  print('Running in', end=' ')
  for i in range(3):
    print('%i...' % (3-i), end=' ')
    sys.stdout.flush()
    time.sleep(1)
  print()
  return response=='yes'
  



all_models = {}

def register(model):
  all_models[model] = []

def unregister(model):
  del all_models[model]

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

def _add_fake_fk_field_hook():
  init = pw.ForeignKeyField.__init__
  def _init(*args, **kwargs):
    self = args[0]
    if 'fake' in kwargs:
      self.fake = kwargs['fake']
      del kwargs['fake']
    init(*args, **kwargs)
  pw.ForeignKeyField.__init__ = _init
_add_fake_fk_field_hook()


def add_evolve():
  pw.Database.evolve = evolve
add_evolve()


__all__ = ['evolve']

