<img src="https://cloud.githubusercontent.com/assets/2049665/17952702/c04e0846-6a32-11e6-8797-60ba50fc0fa6.png" style='width:100%'>

[![Build Status](https://travis-ci.org/keredson/peewee-db-evolve.svg?branch=master)](https://travis-ci.org/keredson/peewee-db-evolve)

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

Functions
---------

The function `evolve(db, interactive=True, ignore_tables=None, schema=None)` is injected into Peewee's database object.

- `interactive` if true will display the proposed changes and prompt you to confirm.  If false will apply them automatically.
- `ignore_tables` takes a list of tables you don't want to evolve for whatever reason.
- `schema` will evolve schemas other than your default schema.

Usage
-----

Write your models as you normall would.  This project will diff the schema defined by your models from the schema
defined in your database, and offer schema changes for your approval.

Renaming columns can be achieved by using the `aka` keyword injected into Peewee's column definition.  For example, if you have:

```python
name = pw.CharField(null=True)
```
And you want to rename it to `full_name`, change your model definition to read:
```python
full_name = pw.CharField(null=True, aka='name')
```
This will generate a RENAME operation instead of a delete then an add.

The parameter `aka` can be either a string or a list (if you have multiple previous names).  Once it's evolved you can
remove it or leave it as you see fit.


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

This project has been in production use since August 2016.  (We switched to Peewee as an ORM.)  But it's a style of schema management I've been using for ~10 years now.

*How can I prevent `peewee-db-evolve` from evolving a specific table or class?*

In the class' `Meta` class, add `evolve = False` and `peewee-db-evolve` will ignore it.  If you don't have a class for a specific table, just make a do-nothing dummy class for it.  Or you can pass in any iterable into the `ignore_tables` kwarg of `evolve()`.

Tests
-----

How to run:

```bash
$ python3 test.py
..................................................................................................
----------------------------------------------------------------------
Ran 110 tests in 49.408s

OK
```

If you get this:
```
EERROR 2002 (HY000): Can't connect to local MySQL server through socket '/var/run/mysqld/mysqld.sock' (2)
```

Something like this should get you going:
```bash
$ sudo apt install mysql-server
[...]

$ sudo cat /etc/mysql/debian.cnf
# Automatically generated for Debian scripts. DO NOT TOUCH!
[client]
host     = localhost
user     = debian-sys-maint
password = XXXXXXXXXXXXX
socket   = /var/run/mysqld/mysqld.sock

$ mysql -u debian-sys-maint -p
Enter password: 
Welcome to the MySQL monitor.  Commands end with ; or \g.
mysql> CREATE USER 'derek'@'localhost';
mysql> GRANT ALL ON *.* TO 'derek'@'localhost';
mysql> flush privileges;
```

Obviously change `derek` to your username.

**WARNING:** This creates an unauthenticated mysql user on your local box.  Don't do this if you have anything important in your local MySQL instance!

<img src="https://travis-ci.org/keredson/peewee-db-evolve.svg">
