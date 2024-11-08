import pytest
from argparse import ArgumentParser, Namespace
from ponderosa.ponderosa import CmdTree

# FILE: ponderosa/test_ponderosa.py


@pytest.fixture
def cmd_tree():
    return CmdTree()


def test_add_child_no_func(cmd_tree):
    root_parser = cmd_tree._root
    child_name = 'child'
    child_parser = cmd_tree._add_child(root_parser, child_name)
    
    assert child_name in cmd_tree._get_subparser_action(root_parser).choices
    assert child_parser.prog == f'{root_parser.prog} {child_name}'
    assert child_parser.get_default('func') is not None


def test_add_child_with_func(cmd_tree):
    root_parser = cmd_tree._root
    child_name = 'child'
    
    def child_func(args: Namespace):
        print("Child function executed")
    
    child_parser = cmd_tree._add_child(root_parser, child_name, func=child_func)
    
    assert child_name in cmd_tree._get_subparser_action(root_parser).choices
    assert child_parser.prog == f'{root_parser.prog} {child_name}'
    assert child_parser.get_default('func') == child_func


def test_add_child_with_aliases(cmd_tree):
    root_parser = cmd_tree._root
    child_name = 'child'
    aliases = ['c', 'ch']
    
    child_parser = cmd_tree._add_child(root_parser, child_name, aliases=aliases)
    
    assert child_name in cmd_tree._get_subparser_action(root_parser).choices
    assert all(alias in cmd_tree._get_subparser_action(root_parser).choices for alias in aliases)
    assert child_parser.prog == f'{root_parser.prog} {child_name}'


def test_add_child_with_help(cmd_tree):
    root_parser = cmd_tree._root
    child_name = 'child'
    help_text = 'This is a child command'
    
    child_parser = cmd_tree._add_child(root_parser, child_name, help=help_text)
    
    assert child_name in cmd_tree._get_subparser_action(root_parser).choices
    assert child_parser.prog == f'{root_parser.prog} {child_name}'
    assert help_text in root_parser.format_help()


def test_get_subparsers_no_subparsers(cmd_tree):
    parser = ArgumentParser()
    subparsers = list(cmd_tree._get_subparsers(parser))
    assert subparsers == []


def test_get_subparsers_with_subparsers(cmd_tree):
    root_parser = cmd_tree._root
    child_name = 'child'
    cmd_tree._add_child(root_parser, child_name)
    
    subparsers = list(cmd_tree._get_subparsers(root_parser))
    assert len(subparsers) == 1
    assert subparsers[0][0] == child_name
    assert isinstance(subparsers[0][-1], ArgumentParser)


def test_get_subparsers_multiple_subparsers(cmd_tree):
    root_parser = cmd_tree._root
    child_names = ['child1', 'child2', 'child3']
    for name in child_names:
        cmd_tree._add_child(root_parser, name)
    
    subparsers = list(cmd_tree._get_subparsers(root_parser))
    assert len(subparsers) == len(child_names)
    for name, _, subparser in subparsers:
        assert name in child_names
        assert isinstance(subparser, ArgumentParser)


def test_find_cmd_root(cmd_tree):
    root_parser = cmd_tree._root
    found_parser = cmd_tree._find_cmd(root_parser.prog)
    
    assert found_parser is root_parser


def test_find_cmd_existing_child(cmd_tree):
    root_parser = cmd_tree._root
    child_name = 'child'
    cmd_tree._add_child(root_parser, child_name)
    
    found_parser = cmd_tree._find_cmd(child_name)
    
    assert found_parser is not None
    assert found_parser.prog == f'{root_parser.prog} {child_name}'


def test_find_cmd_non_existing_child(cmd_tree):
    root_parser = cmd_tree._root
    child_name = 'child'
    
    found_parser = cmd_tree._find_cmd(child_name)
    
    assert found_parser is None


def test_find_cmd_nested_child(cmd_tree):
    root_parser = cmd_tree._root
    parent_name = 'parent'
    child_name = 'child'
    parent_parser = cmd_tree._add_child(root_parser, parent_name)
    cmd_tree._add_child(parent_parser, child_name)
    
    found_parser = cmd_tree._find_cmd(child_name)
    
    assert found_parser is not None
    assert found_parser.prog == f'{root_parser.prog} {parent_name} {child_name}'


def test_find_cmd_repeated_name(cmd_tree):
    '''
    Tests that the _find_cmd method returns the first discovered parser when there are
    multiple parsers with the same name in the command tree.
    '''
    root_parser = cmd_tree._root
    grandparent_name = 'grandparent'
    parent_name = 'parent'
    grandchild_name = 'grandparent'  # Same name as grandparent

    grandparent_parser = cmd_tree._add_child(root_parser, grandparent_name)
    parent_parser = cmd_tree._add_child(grandparent_parser, parent_name)
    cmd_tree._add_child(parent_parser, grandchild_name)

    # Find the grandchild parser
    found_parser = cmd_tree._find_cmd(grandchild_name)

    assert found_parser is grandparent_parser
    assert found_parser.prog == f'{root_parser.prog} {grandparent_name}'


def test_find_cmd_chain_non_existing_root(cmd_tree):
    cmd_fullname = ['non_existing_root', 'child']
    chain = cmd_tree._find_cmd_chain(cmd_fullname)
    assert chain == [None, None]


def test_find_cmd_chain_existing_root_non_existing_leaf(cmd_tree):
    root_parser = cmd_tree._root
    existing_root = cmd_tree._add_child(root_parser, 'existing_root')
    cmd_fullname = ['existing_root', 'non_existing_leaf']
    chain = cmd_tree._find_cmd_chain(cmd_fullname)
    assert chain == [existing_root, None]


def test_find_cmd_chain_all_existing(cmd_tree):
    root_parser = cmd_tree._root
    existing_root = cmd_tree._add_child(root_parser, 'existing_root')
    cmd_tree._add_child(existing_root, 'existing_leaf')
    cmd_fullname = ['existing_root', 'existing_leaf']
    chain = cmd_tree._find_cmd_chain(cmd_fullname)
    assert len(chain) == 2
    assert chain[0].prog == f'{root_parser.prog} existing_root'
    assert chain[1].prog == f'{root_parser.prog} existing_root existing_leaf'


def test_gather_subtree(cmd_tree):
    root_prog = cmd_tree._root.prog

    @cmd_tree.register('grandparent')
    def grandparent_cmd(namespace: Namespace) -> int:
        return 0

    @cmd_tree.register('grandparent', 'parent', 'child')
    def child_cmd(namespace: Namespace) -> int:
        return 0
    
    @cmd_tree.register('grandparent', 'parent', 'sibling')
    def sibling_cmd(namespace: Namespace) -> int:
        return 0
    
    @cmd_tree.register('grandparent', 'aunt', 'cousin')
    def cousin_cmd(namespace: Namespace) -> int:
        return 0

    subtree = cmd_tree.gather_subtree('grandparent')
    assert len(subtree) == 6

    subtree = cmd_tree.gather_subtree('parent')
    assert len(subtree) == 3
    assert [p.prog for p in subtree] == [f'{root_prog} grandparent parent',
                                         f'{root_prog} grandparent parent child',
                                         f'{root_prog} grandparent parent sibling']


def test_gather_subtree_with_aliases(cmd_tree):
    root_prog = cmd_tree._root.prog

    @cmd_tree.register('grandparent', aliases=['gp', 'g'])
    def grandparent_cmd(namespace: Namespace) -> int:
        return 0
    
    @cmd_tree.register('grandparent', 'parent', aliases=['p', 'pa'])
    def parent_cmd(namespace: Namespace) -> int:
        return

    @cmd_tree.register('grandparent', 'parent', 'child', aliases=['c', 'ch'])
    def child_cmd(namespace: Namespace) -> int:
        return 0
    
    @cmd_tree.register('grandparent', 'parent', 'sibling')
    def sibling_cmd(namespace: Namespace) -> int:
        return 0
    
    @cmd_tree.register('grandparent', 'aunt', 'cousin')
    def cousin_cmd(namespace: Namespace) -> int:
        return 0

    subtree = cmd_tree.gather_subtree('grandparent')
    assert len(subtree) == 6

    subtree = cmd_tree.gather_subtree('parent')
    assert len(subtree) == 3
    assert [p.prog for p in subtree] == [f'{root_prog} grandparent parent',
                                         f'{root_prog} grandparent parent child',
                                         f'{root_prog} grandparent parent sibling']


def test_register_cmd_decorator(cmd_tree):
    @cmd_tree.register('test_cmd')
    def test_cmd_func(namespace: Namespace) -> int:
        return 0

    parser = cmd_tree._find_cmd('test_cmd')
    assert parser is not None
    assert parser.prog == f'{cmd_tree._root.prog} test_cmd'
    assert parser._defaults['func'] == test_cmd_func.func


def test_register_cmd_decorator_with_aliases(cmd_tree):
    aliases=['alias1', 'alias2']
    
    @cmd_tree.register('test_cmd', aliases=aliases)
    def test_cmd_func(namespace: Namespace) -> int:
        return 0

    parser = cmd_tree._find_cmd('test_cmd')
    assert parser is not None
    assert parser.prog == f'{cmd_tree._root.prog} test_cmd'
    assert parser._defaults['func'] == test_cmd_func.func
    assert all(alias in cmd_tree._get_subparser_action(cmd_tree._root).choices for alias in aliases)


def test_register_cmd_decorator_with_help(cmd_tree):
    help_text = 'This is a test command'
    
    @cmd_tree.register('test_cmd', help=help_text)
    def test_cmd_func(namespace: Namespace) -> int:
        return 0

    parser = cmd_tree._find_cmd('test_cmd')
    assert parser is not None
    assert parser.prog == f'{cmd_tree._root.prog} test_cmd'
    assert parser._defaults['func'] == test_cmd_func.func
    assert help_text in cmd_tree._root.format_help()


def test_register_cmd_decorator_with_kwargs(cmd_tree):
    desc = 'This is a long description of a test command that should be passed through'
    @cmd_tree.register('test_cmd', description=desc)
    def test_cmd_func(namespace: Namespace) -> int:
        return 0

    parser = cmd_tree._find_cmd('test_cmd')
    assert parser is not None
    assert parser.prog == f'{cmd_tree._root.prog} test_cmd'
    assert parser._defaults['func'] == test_cmd_func.func
    assert parser.description == desc


def test_register_cmd_decorator_nested(cmd_tree):
    @cmd_tree.register('parent')
    def parent_func(namespace: Namespace) -> int:
        return 0

    @cmd_tree.register('parent', 'child')
    def child_func(namespace: Namespace) -> int:
        return 0

    parent_parser = cmd_tree._find_cmd('parent')
    child_parser = cmd_tree._find_cmd('child', parent_parser)

    assert parent_parser is not None
    assert parent_parser.prog == f'{cmd_tree._root.prog} parent'
    assert parent_parser._defaults['func'] == parent_func.func

    assert child_parser is not None
    assert child_parser.prog == f'{cmd_tree._root.prog} parent child'
    assert child_parser._defaults['func'] == child_func.func


def test_common_args_decorator(cmd_tree):

    @cmd_tree.register('grandparent')
    def grandparent_cmd(namespace: Namespace) -> int:
        return 0

    @grandparent_cmd.args(common=True)
    def common_args(parser):
        parser.add_argument('--foo', type=int)

    @cmd_tree.register('grandparent', 'parent', 'child')
    def child_cmd(namespace: Namespace) -> int:
        return 0
    
    @cmd_tree.register('grandparent', 'parent', 'sibling')
    def sibling_cmd(namespace: Namespace) -> int:
        return 0

    args = cmd_tree.parse_args(['grandparent', '--foo', '42'])
    assert args.foo == 42

    args = cmd_tree.parse_args(['grandparent', 'parent', '--foo', '42'])
    assert args.foo == 42

    args = cmd_tree.parse_args(['grandparent', 'parent', 'child', '--foo', '42'])
    assert args.foo == 42

    args = cmd_tree.parse_args(['grandparent', 'parent', 'sibling', '--foo', '42'])
    assert args.foo == 42


def test_common_args_with_aliases(cmd_tree):

    @cmd_tree.register('grandparent', aliases=['gp', 'g'])
    def grandparent_cmd(namespace: Namespace) -> int:
        return 0

    @grandparent_cmd.args(common=True)
    def common_args(parser):
        parser.add_argument('--foo', type=int)

    @cmd_tree.register('grandparent', 'parent', 'child', aliases=['c', 'ch'])
    def child_cmd(namespace: Namespace) -> int:
        return 0
    
    @cmd_tree.register('grandparent', 'parent', 'sibling')
    def sibling_cmd(namespace: Namespace) -> int:
        return 0

    args = cmd_tree.parse_args(['grandparent', '--foo', '42'])
    assert args.foo == 42

    args = cmd_tree.parse_args(['grandparent', 'parent', '--foo', '42'])
    assert args.foo == 42

    args = cmd_tree.parse_args(['grandparent', 'parent', 'child', '--foo', '42'])
    assert args.foo == 42

    args = cmd_tree.parse_args(['grandparent', 'parent', 'sibling', '--foo', '42'])
    assert args.foo == 42


def test_postprocessor_decorator(cmd_tree):
    postprocessed = []

    @cmd_tree.register('test_cmd')
    def test_cmd(namespace: Namespace) -> int:
        return 0
    
    @test_cmd.args()
    def test_cmd_args(parser):
        parser.add_argument('--foo', type=int)

    @test_cmd_args.postprocessor()
    def test_postprocessor(namespace: Namespace):
        postprocessed.append(namespace.foo * 2)

    cmd_tree.run(['test_cmd', '--foo', '42'])
    assert postprocessed[-1] == 84


def test_postprocessor_priorities(cmd_tree):
    postprocessed = []

    @cmd_tree.register('test_cmd')
    def test_cmd(namespace: Namespace) -> int:
        return 0
    
    @test_cmd.args()
    def test_cmd_args(parser):
        parser.add_argument('--foo', type=int)

    @test_cmd_args.postprocessor(priority=0)
    def pp_1(namespace: Namespace):
        assert postprocessed[-1]  == 84
        postprocessed.append(True)

    @test_cmd_args.postprocessor(priority=100)
    def pp_2(namespace: Namespace):
        postprocessed.append(namespace.foo * 2)

    cmd_tree.run(['test_cmd', '--foo', '42'])
    assert postprocessed == [84, True]


def test_postprocessor_priorities_with_common_args(cmd_tree):
    postprocessed = []

    @cmd_tree.register('grandparent')
    def grandparent_cmd(namespace: Namespace) -> int:
        return 0

    @grandparent_cmd.args(common=True)
    def common_args(parser):
        parser.add_argument('--foo', type=int)

    @common_args.postprocessor(priority=50)
    def _(namespace: Namespace):
        postprocessed.append('common')

    @cmd_tree.register('grandparent', 'parent', 'child')
    def child_cmd(namespace: Namespace) -> int:
        return 0

    @child_cmd.args()
    def child_args(parser):
        parser.add_argument('--bar', type=int)

    @child_args.postprocessor(priority=0)
    def child_1(namespace: Namespace):
        postprocessed.append('child_1')

    @child_args.postprocessor(priority=100)
    def child_2(namespace: Namespace):
        postprocessed.append('child_2')

    args = cmd_tree.parse_args(['grandparent', 'parent', 'child', '--foo', '42', '--bar', '21'])
    assert args.foo == 42
    assert args.bar == 21
    assert postprocessed == ['child_2', 'common', 'child_1']