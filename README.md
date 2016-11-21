<img src="https://cloud.githubusercontent.com/assets/2049665/17952702/c04e0846-6a32-11e6-8797-60ba50fc0fa6.png" style='width:100%'>


Peewee DB Evolve
================

Diffs your models against your database, and outputs SQL to (non-destructively) update your schema.

Think of it as `db.create_tables()` on steriods (which doesn't drop your database).

You can also think of it as schema migrations, without having to actually write the migrations.

Quick Start
-----------

1. Run: `sudo pip install peewee-db-evolve`
2. Add `import peeweedbevolve` anywhere before your models are defined.
3. Run `db.evolve()` where you would have normally run `db.create_tables()`, and enjoy!

Example
-------
See our [Hello World](https://github.com/keredson/peewee-db-evolve/tree/master/examples/hello_world) example.

![image](https://cloud.githubusercontent.com/assets/2049665/17993037/1d1c8cf2-6b12-11e6-8591-cd11eb263938.png)


Supported Databases
-------------------

- PostgreSQL
- MySQL

Frequently Asked Questions
--------------------------

*Does this work with existing projects, or only with new projects?*

This works very well with existing projects.  If your API only works with new projects, you're probably doing it wrong.

*Don't you give up control by not writing your own migrations?*

Managing your schema by writing your own migrations is kind of like managing your source code by writing your own `patch` files in addition to writing your actual code.  A well vetted `diff` tool is going to be better and faster at it than you.

*How old / well vetted is this tool?*

I wrote this in August 2016, but it's a port of a tool I've been using for ~10 years now.  (Called [deseb](https://github.com/keredson/deseb), funded by Google's Summer of Code project in 2006, written for Django's ORM.)  There is also a [version for Ruby on Rails](https://github.com/keredson/ruby-db-evolve), which has been used daily in production for ~1.5 years now.  (We're switching to Peewee, hence why I'm doing this port.)

Tests
-----

How to run:

```bash
$ python test.py PostgreSQL
..............................
----------------------------------------------------------------------
Ran 30 tests in 22.421s

OK
```

<img src="https://travis-ci.org/keredson/peewee-db-evolve.svg">
