import os, unittest
import peewee as pw
import peeweedbevolve


# turn on for debugging individual test cases
INTERACTIVE = False

class PostgreSQL(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    os.system('dropdb peeweedbevolve_test 2> /dev/null')

  def setUp(self):
    os.system('createdb peeweedbevolve_test')
    self.db = pw.PostgresqlDatabase('peeweedbevolve_test')
    self.db.connect()
    peeweedbevolve.clear()

  def tearDown(self):
    self.db.close()
    os.system('dropdb peeweedbevolve_test')
  
  def evolve_and_check_noop(self):
    self.db.evolve(interactive=INTERACTIVE)
    self.assertEqual(peeweedbevolve.calc_changes(self.db), [])

  def test_create_table(self):
    class SomeModel(pw.Model):
      some_field = pw.CharField(null=True)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    SomeModel.create(some_field='woot')
    self.assertEqual(SomeModel.select().first().some_field, 'woot')

  def test_create_table_with_fk(self):
    class SomeModel(pw.Model):
      some_field = pw.CharField(null=True)
      class Meta:
        database = self.db
    class SomeModel2(pw.Model):
      some_field2 = pw.CharField(null=True)
      some_model = pw.ForeignKeyField(rel_model=SomeModel)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    sm = SomeModel.create(some_field='woot')
    sm2 = SomeModel2.create(some_field2='woot2', some_model=sm)

  def test_add_fk_column(self):
    class Person(pw.Model):
      class Meta:
        database = self.db
    class Car(pw.Model):
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    peeweedbevolve.unregister(Car)
    class Car(pw.Model):
      owner = pw.ForeignKeyField(rel_model=Person, null=False)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    person = Person.create()
    car = Car.create(owner=person)

  def test_change_int_column_to_fk(self):
    class Person(pw.Model):
      class Meta:
        database = self.db
    class Car(pw.Model):
      owner_id = pw.IntegerField(null=False)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    person = Person.create()
    car = Car.create(owner_id=person.id)
    peeweedbevolve.unregister(Car)
    class Car(pw.Model):
      owner = pw.ForeignKeyField(rel_model=Person, null=False)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(Car.select().first().owner_id, person.id)
    self.assertRaises(pw.IntegrityError, lambda: Car.create(owner=-1))

  def test_change_fk_column_to_int(self):
    class Person(pw.Model):
      class Meta:
        database = self.db
    class Car(pw.Model):
      owner = pw.ForeignKeyField(rel_model=Person, null=False)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    person = Person.create()
    car = Car.create(owner=person)
    peeweedbevolve.unregister(Car)
    class Car(pw.Model):
      owner_id = pw.IntegerField(null=False)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(Car.select().first().owner_id, person.id)
    Car.create(owner_id=-1) # this should not fail

  def test_delete_table(self):
    self.test_create_table()
    peeweedbevolve.clear()
    self.assertEqual(peeweedbevolve.calc_changes(self.db)[0][0].split()[:2], [u'DROP', u'TABLE'])

  def test_rename_table_aka_string(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeOtherModel(pw.Model):
      some_field = pw.CharField(null=True)
      class Meta:
        database = self.db
        aka = 'somemodel'
    self.evolve_and_check_noop()
    self.assertEqual(SomeOtherModel.select().first().some_field, 'woot')

  def test_rename_table_aka_list(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeOtherModel(pw.Model):
      some_field = pw.CharField(null=True)
      class Meta:
        database = self.db
        aka = ['somemodel']
    self.evolve_and_check_noop()
    self.assertEqual(SomeOtherModel.select().first().some_field, 'woot')

  def test_add_column(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_field = pw.CharField(null=True)
      another_field = pw.CharField(null=True)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(SomeModel.select().first().another_field, None)

  def test_rename_column_aka_string(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_other_field = pw.CharField(null=True, aka='some_field')
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(SomeModel.select().first().some_other_field, 'woot')

  def test_rename_column_aka_list(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_other_field = pw.CharField(null=True, aka=['some_field'])
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(SomeModel.select().first().some_other_field, 'woot')

  def test_drop_column(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertFalse(hasattr(SomeModel.select().first(), 'some_field'))

  def test_rename_table_add_column(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeOtherModel(pw.Model):
      some_field = pw.CharField(null=True)
      another_field = pw.CharField(null=True)
      class Meta:
        database = self.db
        aka = 'somemodel'
    self.evolve_and_check_noop()
    o = SomeOtherModel.select().first()
    self.assertEqual(o.some_field, 'woot')
    self.assertEqual(o.another_field, None)

  def test_rename_table_rename_column(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeOtherModel(pw.Model):
      some_other_field = pw.CharField(null=True, aka='some_field')
      class Meta:
        database = self.db
        aka = 'somemodel'
    self.evolve_and_check_noop()
    self.assertEqual(SomeOtherModel.select().first().some_other_field, 'woot')

  def test_rename_table_delete_column(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeOtherModel(pw.Model):
      class Meta:
        database = self.db
        aka = 'somemodel'
    self.evolve_and_check_noop()
    self.assertFalse(hasattr(SomeOtherModel.select().first(), 'some_field'))

  def test_add_not_null_constraint(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_field = pw.CharField(null=False)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(SomeModel.select().first().some_field, 'woot')
    with self.db.atomic() as txn:
      self.assertRaises(pw.IntegrityError, lambda: SomeModel.create())

  def test_remove_not_null_constraint(self):
    self.test_add_not_null_constraint()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_field = pw.CharField(null=True)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    SomeModel.create()

  def test_rename_column_add_not_null_constraint(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_other_field = pw.CharField(null=False, aka='some_field')
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(SomeModel.select().first().some_other_field, 'woot')
    with self.db.atomic() as txn:
      self.assertRaises(pw.IntegrityError, lambda: SomeModel.create())

  def test_rename_table_rename_column_add_not_null_constraint(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeOtherModel(pw.Model):
      some_other_field = pw.CharField(null=False, aka='some_field')
      class Meta:
        database = self.db
        aka = 'somemodel'
    self.evolve_and_check_noop()
    self.assertEqual(SomeOtherModel.select().first().some_other_field, 'woot')
    with self.db.atomic() as txn:
      self.assertRaises(pw.IntegrityError, lambda: SomeOtherModel.create())
  
  def test_add_index(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_field = pw.CharField(index=True, null=True)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True), (u'somemodel', (u'some_field',), False)])

  def test_drop_index(self):
    class SomeModel(pw.Model):
      some_field = pw.CharField(index=True, null=True)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True), (u'somemodel', (u'some_field',), False)])
    peeweedbevolve.clear()
    self.test_create_table()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True),])

  def test_add_index_table_rename(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel2(pw.Model):
      some_field = pw.CharField(index=True, null=True)
      class Meta:
        database = self.db
        aka = 'somemodel'
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel2')), [(u'somemodel2', (u'id',), True), (u'somemodel2', (u'some_field',), False)])

  def test_add_index_column_rename(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_field2 = pw.CharField(index=True, null=True, aka='some_field')
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True), (u'somemodel', (u'some_field2',), False)])

  def test_add_index_table_and_column_rename(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel2(pw.Model):
      some_field2 = pw.CharField(index=True, null=True, aka='some_field')
      class Meta:
        database = self.db
        aka = 'somemodel'
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel2')), [(u'somemodel2', (u'id',), True), (u'somemodel2', (u'some_field2',), False)])

  def test_drop_index_table_rename(self):
    class SomeModel2(pw.Model):
      some_field = pw.CharField(index=True, null=True)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel2')), [(u'somemodel2', (u'id',), True), (u'somemodel2', (u'some_field',), False)])
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_field = pw.CharField(null=True)
      class Meta:
        database = self.db
        aka = 'somemodel2'
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True),])

  def test_add_unique(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_field = pw.CharField(unique=True, null=True)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True), (u'somemodel', (u'some_field',), True)])

  def test_drop_unique(self):
    class SomeModel(pw.Model):
      some_field = pw.CharField(unique=True, null=True)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True), (u'somemodel', (u'some_field',), True)])
    peeweedbevolve.clear()
    self.test_create_table()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True),])

  def test_add_multi_index(self):
    self.test_create_table()
    peeweedbevolve.clear()
    class SomeModel(pw.Model):
      some_field = pw.CharField(null=True)
      class Meta:
        database = self.db
        indexes = (
            (('id', 'some_field'), False),
        )
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True), (u'somemodel', (u'id',u'some_field'), False)])

  def test_drop_multi_index(self):
    class SomeModel(pw.Model):
      some_field = pw.CharField(null=True)
      class Meta:
        database = self.db
        indexes = (
            (('id', 'some_field'), False),
        )
    self.evolve_and_check_noop()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True), (u'somemodel', (u'id',u'some_field'), False)])
    peeweedbevolve.clear()
    self.test_create_table()
    self.assertEqual(peeweedbevolve.normalize_indexes(self.db.get_indexes('somemodel')), [(u'somemodel', (u'id',), True),])




# SQLite doesn't work yet!
class SQLite(PostgreSQL):
  @classmethod
  def setUpClass(cls):
    os.system('rm /tmp/peeweedbevolve_test.db')

  def setUp(self):
    self.db = pw.SqliteDatabase('/tmp/peeweedbevolve_test.db')
    self.db.connect()
    peeweedbevolve.clear()

  def tearDown(self):
    self.db.close()
    os.system('rm /tmp/peeweedbevolve_test.db')


if __name__ == "__main__":
   unittest.main()

