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

@foobar_args.postprocessor(priority=100)
def _(args: Namespace):
    print(f'High priority: {args}')
    args.calculated = args.bar * 2

if __name__ == '__main__':    
    commands.run()