import os, unittest
import peewee as pw
import peeweedbevolve


class PostgresTestCase(unittest.TestCase):

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
    self.db.evolve(interactive=False)
    self.assertEqual(peeweedbevolve.calc_changes(self.db), [])

  def test_create_table(self):
    class SomeModel(pw.Model):
      some_field = pw.CharField(null=True)
      class Meta:
        database = self.db
    self.evolve_and_check_noop()
    SomeModel.create(some_field='woot')
    self.assertEqual(SomeModel.select().first().some_field, 'woot')

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



if __name__ == "__main__":
   unittest.main()

