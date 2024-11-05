#!/usr/bin/env python3

from argparse import Namespace
from ponderosa import arggroup, ArgParser, CmdTree

commands = CmdTree()

@commands.register('foobar')
def foobar_cmd(args: Namespace) -> int:
    print(f'Handling subcommand with args: {args}')
    return 0

@foobar_cmd.args()
def foobar_args(group: ArgParser):
    group.add_argument('--foo', type=str)
    group.add_argument('--bar', type=int, default=21)

@foobar_args.postprocessor()
def _(args: Namespace):
    print(f'foobar_args postproc: low priority: {args}')

@commands.register('bizzbazz')
def bizzbazz_cmd(args: Namespace) -> int:
    print(f'Handling subcommand with args: {args}')
    return 0

@bizzbazz_cmd.args()
def bizzbazz_args(group: ArgParser):
    group.add_argument('--bizz', type=str)
    group.add_argument('--bazz', type=int, default=42)

@bizzbazz_args.postprocessor(priority=50)
def _(args: Namespace):
    print(f'bizzbazz_args postproc: medium priority: {args}')

@commands.root.args('common args', common=True)
def common_args(group: ArgParser):
    group.add_argument('--common', type=str)

@common_args.postprocessor(priority=100)
def _(args: Namespace):
    print(f'common_args postproc: high priority: {args}')
    args.calculated = getattr(args, 'bar', getattr(args, 'bazz', 42)) * 2

if __name__ == '__main__':    
    commands.run()