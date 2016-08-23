Peewee DB Evolve
================

Diffs your schema against your model files, and changes the schema to match.

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
