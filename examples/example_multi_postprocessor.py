#!/usr/bin/env python3

from argparse import ArgumentParser, Namespace
from pothos import CmdTree, arggroup

commands = CmdTree()

@commands.register('foobar')
def foobar_cmd(args: Namespace) -> int:
    print(f'Handling subcommand with args: {args}')
    return 0

@foobar_cmd.args()
def foobar_args(group: ArgumentParser):
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