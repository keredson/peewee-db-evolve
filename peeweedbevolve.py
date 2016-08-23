import peewee as pw
import playhouse.migrate


# default value for interactive
interactive = True


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
  raise Exception("could not auto-detect migrator for %s - please provide one via the migrator kwarg" % repr(db.__class__.__name__))

def normalize_column_type(t):
  if t in ['serial']: t = 'integer'
  if t in ['character varying']: t = 'varchar'
  if t in ['timestamp without time zone']: t = 'timestamp'
  return unicode(t)
  
def normalize_field_type(field):
  t = field.get_column_type().lower()
  return normalize_column_type(t)
  
def can_convert(type1, type2):
  return True

def calc_column_changes(ntn, existing_columns, defined_fields):
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

  return new_cols, delete_cols, rename_cols

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
    to_run += [qc.parse_node(op) for op in migrator.rename_table(k,v, generate=True)]


  rename_cols_by_table = {}
  for etn, ecols in existing_columns.items():
    if etn in table_deletes: continue
    ntn = table_renames.get(etn, etn)
    dcols = table_names_to_models[ntn]._meta.sorted_fields
    defined_column_name_to_field = {unicode(f.db_column):f for f in dcols}
    adds, deletes, renames = calc_column_changes(ntn, ecols, dcols)
    for column_name in adds:
      operation = migrator.alter_add_column(ntn, column_name, defined_column_name_to_field[column_name], generate=True)
      to_run.append(qc.parse_node(operation))
    for column_name in deletes:
      operation = migrator.drop_column(ntn, column_name, generate=True, cascade=False)
      to_run.append(qc.parse_node(operation))
    for ocn, ncn in renames.items():
      operation = migrator.rename_column(ntn, ocn, ncn, generate=True)
      to_run.append(qc.parse_node(operation))
    rename_cols_by_table[ntn] = renames
  
  '''
  to_run += calc_index_changes(existing_indexes, $schema_indexes, renames, rename_cols_by_table)

  to_run += calc_fk_changes($foreign_keys, Set.new(existing_tables.keys), renames)

  to_run += calc_perms_changes($schema_tables, noop) unless $check_perms_for.empty?

  to_run += sql_drops(deletes)
  '''

  
  
  to_run += [qc.parse_node(pw.Clause(pw.SQL('DROP TABLE'), pw.Entity(tbl))) for tbl in table_deletes]
  return to_run
  
def evolve(db, interactive=None):
  to_run = calc_changes(db)
  if interactive is None:
    interactive = globals()['interactive']

  with db.atomic() as txn:
    for sql, params in to_run:
      print sql
      db.execute_sql(sql, params)



all_models = {}

def register(model):
  all_models[model] = []

def clear():
  all_models.clear()

def add_model_hook():
  init = pw.BaseModel.__init__
  def _init(*args, **kwargs):
    cls = args[0]
    fields = args[3]
    if '__module__' in fields:
      del fields['__module__']
    register(cls)
    init(*args, **kwargs)
  pw.BaseModel.__init__ = _init
add_model_hook()

def add_field_hook():
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
add_field_hook()


def add_evolve():
  pw.Database.evolve = evolve
add_evolve()


__all__ = ['evolve']

