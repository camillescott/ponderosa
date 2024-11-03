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
