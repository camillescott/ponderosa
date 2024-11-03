from argparse import Namespace
from ponderosa import ArgParser, CmdTree

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