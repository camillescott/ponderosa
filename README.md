# ponderosa: ergonomic subcommand handling built on argparse

![PyPI - Version](https://img.shields.io/pypi/v/ponderosa?link=https%3A%2F%2Fpypi.org%2Fproject%2Fponderosa%2F) ![Tests](https://github.com/camillescott/ponderosa/actions/workflows/pytest.yml/badge.svg) [![codecov](https://codecov.io/github/camillescott/ponderosa/graph/badge.svg?token=XSESR7TKXJ)](https://codecov.io/github/camillescott/ponderosa) <a href="https://github.com/camillescott/ponderosa/blob/latest/LICENSE"><img alt="License: 3-Clause BSD" src="https://img.shields.io/badge/License-BSD%203--Clause-blue.svg"></a> ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ponderosa) ![Static Badge](https://img.shields.io/badge/Platforms-Linux%20%7C%20MacOS%20%7C%20Windows-blue)

Ponderosa extends the Python standard library's [argparse](https://docs.python.org/3/library/argparse.html) in an effort to make dealing with deeply nested subcommand trees less ponderous. 
I've tried out many different command line parsing libraries over the years, but none of them have quite scratched the itch for this use case.
Ponderosa gets rid of those giant blocks of `add_subparsers` nastiness without entirely reinventing the wheel at the lower level of parsing the arguments themselves.

## Basic Usage

```python
from argparse import Namespace
from ponderosa import ArgParser, CmdTree
# ArgParser is just Union[argparse.ArgumentParser, argparse._ArgumentGroup]

commands = CmdTree(description='Ponderosa Basics')

@commands.register('basics', help='Easy as pie 🥧')
def basics_cmd(args: Namespace):
    print('Ponderosa 🌲')
    if args.show:
        commands.print_help()

@basics_cmd.args()
def _(parser: ArgParser):
    parser.add_argument('--show', action='store_true', default=False)

@commands.register('basics', 'deeply', 'nested', help='A deeply nested command')
def deeply_nested_cmd(args: Namespace):
    print(f'Deeply nested command! Args: {args}')

@commands.register('basics', 'deeply', 'also-nested', help='Another deeply nested command')
def deeply_nested_cmd(args: Namespace):
    print(f'Another deeply nested command! Args: {args}')

@deeply_nested_cmd.args()
def _(parser: ArgParser):
    parser.add_argument('--deep', action='store_true', default=False)

if __name__ == '__main__':
    commands.run()
```

```console
$ python examples/basics.py basics --show
Ponderosa 🌲
usage: basics.py [-h] {basics} ...

Subcommands:
  basics: Easy as pie 🥧
    deeply: 
      nested: A deeply nested command
      also-nested: Another deeply nested command

$ python examples/basics.py basics deeply nested -h
usage: basics.py basics deeply nested [-h] [--deep]

options:
  -h, --help  show this help message and exit
  --deep
```


## Registering Subcommands




## Add Postprocessors

Sometimes you want to add some postprocessing to your arguments that can only be done after parsing has already
occurred - for example, validating one of your arguments might depend on opening a database connection.
You can register postprocessors on your argument groups to handle this:

```python
#!/usr/bin/env python3

from argparse import Namespace
from ponderosa import arggroup, ArgParser, CmdTree

commands = CmdTree()

@arggroup('Foobar')
def foobar_args(group: ArgParser):
    group.add_argument('--foo', type=str)
    group.add_argument('--bar', type=int)
    
@foobar_args.apply()
@commands.register('foobar')
def foobar_cmd(args: Namespace) -> int:
    print(f'Handling subcommand with args: {args}')
    return 0
    
@foobar_args.postprocessor()
def foobar_postprocessor(args: Namespace):
    print(f'Postprocessing args: {args}')

if __name__ == '__main__':    
    commands.run()
```

Running the example gives, roughly:

```console
$ python examples/postprocessor.py foobar --bar 1 --foo bar      
Postprocessing args: Namespace(func=<function foobar_cmd at 0x7bc1ba0b1800>, foo='bar', bar=1)
Handling subcommand with args: Namespace(func=<function foobar_cmd at 0x7bc1ba0b1800>, foo='bar', bar=1)
```

We can of course register multiple postprocessors, and do so on the result of a `SubCmd.args`.
By default, the postprocessors will be executed in the order they are registered:

```python
#!/usr/bin/env python3

from argparse import Namespace
from ponderosa import ArgParser, CmdTree

commands = CmdTree()

@commands.register('foobar')
def foobar_cmd(args: Namespace) -> int:
    print(f'Handling subcommand with args: {args}')
    return 0

@foobar_cmd.args()
def foobar_args(group: ArgParser):
    group.add_argument('--foo', type=str)
    group.add_argument('--bar', type=int)
    
@foobar_args.postprocessor()
def _(args: Namespace):
    print(f'First postprocessor: {args}')
    args.calculated = args.bar * 2

@foobar_args.postprocessor()
def _(args: Namespace):
    print(f'Second postprocessor: {args}')

if __name__ == '__main__':    
    commands.run()
```

Which gives:

```console
$ python examples/multi_postprocessor.py foobar --foo bar --bar 1
SubCmd.args.wrapper: foobar
First postprocessor: Namespace(func=<function foobar_cmd at 0x751415cb1a80>, foo='bar', bar=1)
Second postprocessor: Namespace(func=<function foobar_cmd at 0x751415cb1a80>, foo='bar', bar=1, calculated=2)
Handling subcommand with args: Namespace(func=<function foobar_cmd at 0x751415cb1a80>, foo='bar', bar=1, calculated=2)
```

You can also provide a priority to your postprocessors if registration order is insufficient:

```python
#!/usr/bin/env python3

from argparse import Namespace
from ponderosa import ArgParser, CmdTree

commands = CmdTree()

@commands.register('foobar')
def foobar_cmd(args: Namespace) -> int:
    print(f'Handling subcommand with args: {args}')
    return 0

@foobar_cmd.args()
def foobar_args(group: ArgParser):
    group.add_argument('--foo', type=str)
    group.add_argument('--bar', type=int)

@foobar_args.postprocessor()
def _(args: Namespace):
    print(f'Low priority: {args}')

# Usually, this function would run second, as it was defined second.
# It will run first due to its priority score.
@foobar_args.postprocessor(priority=100)
def _(args: Namespace):
    print(f'High priority: {args}')
    args.calculated = args.bar * 2

if __name__ == '__main__':    
    commands.run()
```

This time, we get:

```console
$ python examples/priority_postprocessors.py foobar --bar 2 
High priority: Namespace(func=<function foobar_cmd at 0x7693e57b5bc0>, foo=None, bar=2)
Low priority: Namespace(func=<function foobar_cmd at 0x7693e57b5bc0>, foo=None, bar=2, calculated=4)
Handling subcommand with args: Namespace(func=<function foobar_cmd at 0x7693e57b5bc0>, foo=None, bar=2, calculated=4)
```