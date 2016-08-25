<img src="https://cloud.githubusercontent.com/assets/2049665/17952702/c04e0846-6a32-11e6-8797-60ba50fc0fa6.png" style='width:100%'>


Peewee DB Evolve
================

Diffs your models against your database, and outputs SQL to (non-destructively) update your schema.

Think of it as `db.create_tables()` on steriods (which doesn't drop your database).

Example
-------
Our local `evolve.py`:
```python
import peeweedbevolve
import config
import models

if __name__=='__main__':
  config.db.evolve()
```

Running it:
```bash
$ python evolve.py

------------------
 peewee-db-evolve
------------------

Your database needs the following change:

  ALTER TABLE somemodel ADD COLUMN another_field VARCHAR(255);

Do you want to run this command? (type yes or no) yes
Running in 3... 2... 1...

  ALTER TABLE somemodel ADD COLUMN another_field VARCHAR(255) []

SUCCESS!
https://github.com/keredson/peewee-db-evolve
```



Tests
-----

```bash
peewee-db-evolve$ python -m test PostgreSQL
...............
----------------------------------------------------------------------
Ran 15 tests in 8.572s

OK
```
