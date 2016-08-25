Hello World
===========

Let's look at an example peewee model in `step1.py`:

```python
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

```

Notice we call `db.evolve()` rather than `db.create_tables([Person])`.  This will create our initial table (assuming we just created Postgres database `example_hello_world`).

Run it:

```sql
$ python step1.py 

------------------
 peewee-db-evolve
------------------

Your database needs the following change:

  BEGIN TRANSACTION;
  CREATE TABLE person (id SERIAL NOT NULL PRIMARY KEY, first_name VARCHAR(255), birthday DATE, is_relative BOOLEAN NOT NULL);
  COMMIT;

Do you want to run this command? (type yes, no or test) 
```

By default `db.evolve()` runs in interactive mode to allow you to preview the changes.  Type `yes` to apply:

```bash
Running in 3... 2... 1...

  CREATE TABLE person (id SERIAL NOT NULL PRIMARY KEY, first_name VARCHAR(255), birthday DATE, is_relative BOOLEAN NOT NULL) []

SUCCESS!
```

Your table now exists!

Oh no, but we forgot `last_name`.  Let's update our model in `step2.py`:

```python
import peeweedbevolve
import peewee as pw

db = pw.PostgresqlDatabase('example_hello_world')

class Person(pw.Model):
  first_name = pw.CharField(null=True)
  last_name = pw.CharField(null=True)
  birthday = pw.DateField(null=True)
  is_relative = pw.BooleanField(default=False)

  class Meta:
    database = db
    
db.evolve()
```

Notice the `last_name` field was added.  Now let's run again:

```sql
$ python step2.py 

------------------
 peewee-db-evolve
------------------

Your database needs the following change:

  BEGIN TRANSACTION;
  ALTER TABLE person ADD COLUMN last_name VARCHAR(255);
  COMMIT;

Do you want to run this command? (type yes, no or test) yes
Running in 3... 2... 1...

  ALTER TABLE person ADD COLUMN last_name VARCHAR(255) []

SUCCESS!
```

Voila!
