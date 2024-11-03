# ponderosa: ergonomic subcommand handling built on argparse

![PyPI - Version](https://img.shields.io/pypi/v/ponderosa) ![Tests](https://github.com/camillescott/ponderosa/actions/workflows/pytest.yml/badge.svg) [![codecov](https://codecov.io/github/camillescott/ponderosa/graph/badge.svg?token=XSESR7TKXJ)](https://codecov.io/github/camillescott/ponderosa)

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
    
@foobar_args.postprocessor
def foobar_postprocessor(args: Namespace):
    print(f'Postprocessing args: {args}')

if __name__ == '__main__':    
    commands.run()
```

Running the example gives, roughly:

```console
$ python example_postprocessor.py foobar --bar 1 --foo bar      
Postprocessing args: Namespace(func=<function foobar_cmd at 0x7bc1ba0b1800>, foo='bar', bar=1)
Handling subcommand with args: Namespace(func=<function foobar_cmd at 0x7bc1ba0b1800>, foo='bar', bar=1)
```

We can of course register multiple postprocessors, and do so on the result of a `SubCmd.args`.
The postprocessors will be executed in the order they are registered:

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
    
@foobar_args.postprocessor
def _(args: Namespace):
    print(f'First postprocessor: {args}')
    args.calculated = args.bar * 2

@foobar_args.postprocessor
def _(args: Namespace):
    print(f'Second postprocessor: {args}')

if __name__ == '__main__':    
    commands.run()
```

Which gives:

```console
$ python example_multi_postprocessor.py foobar --foo bar --bar 1
SubCmd.args.wrapper: foobar
First postprocessor: Namespace(func=<function foobar_cmd at 0x751415cb1a80>, foo='bar', bar=1)
Second postprocessor: Namespace(func=<function foobar_cmd at 0x751415cb1a80>, foo='bar', bar=1, calculated=2)
Handling subcommand with args: Namespace(func=<function foobar_cmd at 0x751415cb1a80>, foo='bar', bar=1, calculated=2)
```