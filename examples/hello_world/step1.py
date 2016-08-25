import peeweedbevolve
import peewee as pw

db = pw.PostgresqlDatabase('example_hello_world')

class Person(pw.Model):
  first_name = pw.CharField(null=True)
  birthday = pw.DateField(null=True)
  is_relative = pw.BooleanField(default=False)

  class Meta:
    database = db
    
db.evolve() # call this instead of db.create_tables([Person])


