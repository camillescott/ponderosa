#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) Camille Scott, 2024
# File   : ponderosa.py
# License: BSD 3-Clause
# Author : Camille Scott <camille@bogg.cc>
# Date   : 02.11.2024

from argparse import (Action,
                      ArgumentParser, 
                      _ArgumentGroup,
                      Namespace,
                      _SubParsersAction)
from collections import deque
from functools import wraps
from itertools import pairwise
from typing import Callable, Type


Subparsers = _SubParsersAction
NamespaceFunc = Callable[[Namespace], int | None]
ArgParser = ArgumentParser | _ArgumentGroup
ArgAdderFunc = Callable[[ArgParser], Action | None]


class SubCmd:
    '''
    Represents a subcommand in the command tree.

    Args:
        parser (ArgumentParser): The argument parser for the subcommand.
        name (str): The name of the subcommand.
        cmd_tree (CmdTree): The command tree the subcommand belongs to.
    '''

    def __init__(self, parser: ArgumentParser,
                       name: str,
                       cmd_tree: 'CmdTree'):
        self.parser = parser
        self.name = name
        self.cmd_tree = cmd_tree

    def args(self, groupname: str | None = None,
                   desc: str | None = None,
                   common: bool = False):
        '''
        Registers arguments for the subcommand.

        Args:
            groupname (str | None, optional): Name of the argument group.
            desc (str | None, optional): Description of the argument group.
            common (bool, optional): If True, registers common arguments across subcommands.

        Returns:
            Callable: The argument wrapper function.
        '''
        
        def wrapper(arg_adder: ArgAdderFunc):
            group = ArgGroup(groupname, arg_adder, desc=desc)
            apply_func = group.apply(common=common)
            apply_func(self)
            return group
        return wrapper

    @property
    def func(self):
        '''
        Gets the function associated with the subcommand.

        Returns:
            Callable: The function set via 'set_defaults' in ArgumentParser.
        '''
        return self.parser._defaults['func']

    @func.setter
    def func(self, new_func: NamespaceFunc):
        '''
        Sets the function associated with the subcommand.

        Args:
            new_func (NamespaceFunc): The function to set.
        '''
        self.parser._defaults['func'] = new_func


class CmdTree:
    '''
    Manages a tree of subparsers and facilitates registering functions
    for the subcommands.

    Args:
        root (ArgumentParser | None, optional): The root parser of the command tree.
        **kwargs: Additional arguments passed to the ArgumentParser.
    '''

    def __init__(self, root: ArgumentParser | None = None, **kwargs):
        '''
        Initializes the CmdTree with a root parser.
        '''
        if root is None:
            self._root = ArgumentParser(**kwargs)
        else:
            self._root = root
        self._root.set_defaults(func = lambda _: self._root.print_help())
        if not self._get_subparsers(self._root):
            self._root.add_subparsers()
        self._root._cmd_tree = self
        
        self.root = SubCmd(self._root, self._root.prog, self)
        self.common_adders: list[tuple[str | None, ArgAdderFunc]] = []
        self.common_applied: set[tuple[ArgParser, ArgAdderFunc]] = set()
        self.postprocessors_q: list[tuple[int, NamespaceFunc]] = []

    def parse_args(self, *args, **kwargs):
        '''
        Parses command-line arguments.

        Args:
            *args: Variadic positional arguments for ArgumentParser.
            **kwargs: Variadic keyword arguments for ArgumentParser.

        Returns:
            Namespace: The collected argument Namespace.
        '''
        self._apply_common_args()
        parsed = self._root.parse_args(*args, **kwargs)
        self._run_postprocessors(parsed)
        return parsed

    def run(self, *args, **kwargs) -> int:
        parsed = self.parse_args(*args, **kwargs)
        if (retcode := parsed.func(parsed)) is None:
            return 0
        return retcode

    def enqueue_postprocessor(self, func: NamespaceFunc, priority: int = 0):
        '''
        Enqueues a postprocessor function to run after argument parsing.

        Args:
            func (NamespaceFunc): The postprocessor function to enqueue.
            priority (int, optional): The priority of the postprocessor.
        '''
        if (priority, func) not in self.postprocessors_q:
            self.postprocessors_q.append((priority, func))

    def _run_postprocessors(self, args: Namespace):
        '''
        Runs postprocessors on the provided Namespace.

        Args:
            args (Namespace): The Namespace to postprocess.
        '''
        from rich import print
        funcs = sorted(self.postprocessors_q, key=lambda func_tuple: func_tuple[0], reverse=True)
        for _, postproc_func in funcs:
            postproc_func(args)

    def _get_subparser_action(self, parser: ArgumentParser) -> _SubParsersAction | None:
        '''
        Extracts the subparser action from the provided parser.

        Args:
            parser (ArgumentParser): The argument parser to search.

        Returns:
            _SubParsersAction | None: The extracted subparser action, if found.
        '''
        for action in parser._actions:
            if isinstance(action, _SubParsersAction):
                return action
        return None

    def _get_subparsers(self, parser: ArgumentParser):
        '''
        Retrieves subparsers for the provided parser.

        Args:
            parser (ArgumentParser): The parser for which subparsers are retrieved.

        Yields:
            Tuple: Name and argument parser for each subparser.
        '''
        action = self._get_subparser_action(parser)
        if action is not None:
            for subaction in action._get_subactions():
                yield subaction.dest, subaction, action.choices[subaction.dest]

    def _find_cmd(self, cmd_name: str, root: ArgumentParser | None = None) -> ArgumentParser | None:
        '''
        Finds a subcommand by its name, performing a breadth-first search.

        Args:
            cmd_name (str): The name of the subcommand to find.
            root (ArgumentParser | None, optional): The parser to start at. Defaults to root parser.

        Returns:
            ArgumentParser | None: The subcommand parser, or None if not found.
        '''
        if root is None:
            root = self._root
        
        if cmd_name == root.prog:
            return root

        subparser_deque = deque(self._get_subparsers(root))
        while subparser_deque:
            root_name, _, root_parser = subparser_deque.popleft()
            if root_name == cmd_name:
                return root_parser
            else:
                subparser_deque.extend(self._get_subparsers(root_parser))
        return None

    def _walk_subtree(self,
                      parser: ArgParser,
                      found: list[tuple[int, ArgParser, Type[Subparsers._ChoicesPseudoAction] | None]],
                      level: int,
                      visitor: Callable[[int,
                                         ArgumentParser,
                                         Type[Subparsers._ChoicesPseudoAction] | None,
                                         ArgumentParser | None],
                                         None] | None = None):
        
        for _, subparser_action, subparser in self._get_subparsers(parser):
            if visitor is not None:
                visitor(level, subparser, subparser_action, parser)
            found.append((level, subparser, subparser_action))
            self._walk_subtree(subparser, found, level=level+1, visitor=visitor) 

    def walk_subtree(self, root_name: str | None,
                           visitor: Callable[[int,
                                              ArgumentParser,
                                              Type[Subparsers._ChoicesPseudoAction] | None],
                                              None] | None = None):
        '''
        Walks the subtree starting from the provided root name.

        Args:
            root_name (str | None): The root subparser name to start walking from.
            visitor (Callable[[ArgumentParser], None]): The visitor function to call on each subparser.
        '''
        if root_name is None:
            root = self._root
        else:
            root = self._find_cmd(root_name)
        if root is None:
            return []
        
        found = [(0, root, None)]
        self._walk_subtree(root, found, 1, visitor=visitor)

        return found
    
    def gather_subtree(self, root_name: str | None) -> list[ArgumentParser]:
        '''
        Gathers all subparsers starting from the provided root name.

        Args:
            root_name (str | None): The root subparser name to start gathering from.

        Returns:
            list[ArgumentParser]: List of the collected argument parsers in the subtree.
        '''
        found = self.walk_subtree(root_name)
        return [f[1] for f in found]
        

    def _find_cmd_chain(self, cmd_fullname: list[str]) -> list[ArgumentParser | None]:
        '''
        Finds a command chain of subcommands from a fullname list.

        Args:
            cmd_fullname (list[str]): List representing the command chain.

        Returns:
            list[ArgumentParser | None]: List of argument parsers corresponding to the chain.
        '''
        root_name = cmd_fullname[0]
        if (root_parser := self._find_cmd(root_name)) is None:
            return [None] * len(cmd_fullname)
        elif len(cmd_fullname) == 1:
            return [root_parser]
        else:
            chain : list[ArgumentParser | None] = [root_parser]
            for next_name in cmd_fullname[1:]:
                found = False
                for child_name, _, child_parser in self._get_subparsers(root_parser):
                    if child_name == next_name:
                        root_parser = child_parser
                        chain.append(child_parser)
                        found = True
                        break
                if not found:
                    break
            if len(chain) != len(cmd_fullname):
                chain.extend([None] * (len(cmd_fullname) - len(chain)))
            return chain

    def _add_child(self, root: ArgumentParser,
                         child_name: str,
                         func = None,
                         aliases: list[str] | None = None,
                         help: str | None = None,
                         **parser_kwargs):
        '''
        Adds a child subparser to the root parser.

        Args:
            root (ArgumentParser): The root parser.
            child_name (str): The name for the child subparser.
            func (Callable, optional): The function to associate with the child subcommand.
            aliases (list[str] | None, optional): Aliases for the child subcommand.
            help (str | None, optional): Help text for the child subcommand.

        Returns:
            ArgumentParser: The added child subparser.
        '''
        if (subaction := self._get_subparser_action(root)) is None:
            subaction = root.add_subparsers()
        child = subaction.add_parser(child_name, help=help, aliases=aliases if aliases else [], **parser_kwargs)
        cmd_func = (lambda _: child.print_help()) if func is None else func
        child.set_defaults(func=cmd_func)
        child._cmd_tree = self
        return child

    def register_cmd(self, cmd_fullname: list[str],
                           cmd_func: NamespaceFunc,
                           aliases: list[str] | None = None,
                           help: str | None = None,
                           **parser_kwargs) -> ArgumentParser:
        '''
        Registers a fully qualified command name with a function.

        Args:
            cmd_fullname (list[str]): The full name of the command.
            cmd_func (NamespaceFunc[P]): The function associated with the command.
            aliases (list[str] | None, optional): Aliases of the subcommand.
            help (str | None, optional): Help text for the subcommand.

        Returns:
            ArgumentParser: The registered subcommand parser.
        '''
        chain = self._find_cmd_chain(cmd_fullname)
        if not any(map(lambda el: el is None, chain)):
            raise ValueError(f'subcommand {cmd_fullname} already registered')
        if chain[0] is None:
            chain = [self._root] + chain
            cmd_fullname = [self._root.prog] + cmd_fullname
        leaf_name = cmd_fullname[-1]
        for i, j in pairwise(range(len(chain))):
            if chain[j] is None:
                if chain[i] is None:
                    raise ValueError(f'Bad argument chain: {chain[i]}->{chain[j]}')
                elif cmd_fullname[j] == leaf_name:
                    return self._add_child(chain[i], leaf_name, func=cmd_func, aliases=aliases, help=help, **parser_kwargs)
                else:
                    child = self._add_child(chain[i], cmd_fullname[j])
                    chain[j] = child
        raise ValueError(f'{leaf_name} was not registered')

    def register(self, *cmd_fullname: str,
                       aliases: list[str] | None = None,
                       help: str | None = None,
                       **parser_kwargs):
        '''
        Registers a new subcommand with the CmdTree.

        Args:
            *cmd_fullname (str): Variable-length subcommand name string.
            aliases (list[str] | None, optional): Aliases of the subcommand.
            help (str | None, optional): Help text for the subcommand.

        Returns:
            Callable: The subcommand wrapper.
        '''
        def wrapper(cmd_func: NamespaceFunc):
            return SubCmd(self.register_cmd(list(cmd_fullname),
                                            cmd_func,
                                            aliases=aliases,
                                            help=help,
                                            **parser_kwargs),
                          cmd_fullname[-1],
                          self)
        return wrapper

    def register_common_args(self, cmd_root: str | None, arg_adder: ArgAdderFunc):
        '''
        Registers common arguments across multiple subcommands.

        Args:
            cmd_root (str | None): The root command to apply common arguments.
            arg_adder (ArgAdderFunc): Function that adds arguments.
        '''
        self.common_adders.append((cmd_root, arg_adder))

    def _apply_common_args(self):
        '''
        Applies the registered common arguments to their respective parsers.
        '''
        for root_name, arg_adder in self.common_adders:
            for parser in self.gather_subtree(root_name):
                if (parser, arg_adder) not in self.common_applied:
                    arg_adder(parser)
                    self.common_applied.add((parser, arg_adder))

    def __rich__(self):
        from rich.console import Console, Group
        from rich.panel import Panel
        from rich.tree import Tree

        width = max(Console().width // 2, 80)
        tree = Tree(self._root.prog, guide_style='uu magenta')
        nodes = {self._root: tree}
        
        def visitor(level, subparser, pseudoaction, parent):
            if self._get_subparser_action(subparser) is None:
                # leaf node
                element = Group(self._format_subparser(pseudoaction),
                                Panel(subparser.format_help(),
                                      width=width))
            else:
                element = self._format_subparser(pseudoaction)
            node = nodes[parent].add(element)
            nodes[subparser] = node
        
        self.walk_subtree(None, visitor)

        return tree

    def _format_subparser(self, pseudoaction):
        '''
        Formats a subparser and its subparsers into a string.

        Args:
            pseudoaction (_ChoicesPseudoAction): The pseudoaction to format.

        Returns:
            str: The formatted subparser string.
        '''
        help = pseudoaction.help or ''
        try:
            import rich
        except ImportError:
            return f'{pseudoaction.metavar}: {help}'
        else:
            return f'[bold]{pseudoaction.metavar}[/bold]: {help}'

    def format_help(self):
        '''
        Prints the help information for the entire command tree.
        '''
        cmds = [self._root.format_usage(),
                f'{self._root.prog}:']
        
        def visitor(level, subparser, pseudoaction, parent):
            if pseudoaction:
                cmds.append('  ' * level + self._format_subparser(pseudoaction))
        self.walk_subtree(None, visitor)

        return '\n'.join(cmds)


class ArgGroup:
    '''
    Represents a group of arguments for an argument parser or subcommand.

    Args:
        group_name (str | None): The name of the argument group.
        arg_func (ArgAdderFunc): The function that adds arguments to the group.
        desc (str | None, optional): Description of the argument group.
    '''

    def __init__(self, group_name: str | None,
                       arg_func: ArgAdderFunc,
                       desc: str | None = None):
        self.group_name = group_name
        self.arg_func = arg_func
        self.desc = desc
        self.postprocessors: list[tuple[int, NamespaceFunc]] = []

    def apply(self, common: bool = False, *args, **kwargs):
        '''
        Applies the argument group to a parser.

        Args:
            common (bool, optional): If True, registers the argument group as a common group.
            *args: Additional arguments passed to the argument adder function.
            **kwargs: Additional keyword arguments passed to the argument adder function.

        Returns:
            Callable: The apply wrapper function.
        '''

        def _apply_group(parser: ArgumentParser):
            if self.group_name is None:
                group = parser
            else:
                group = parser.add_argument_group(title=self.group_name,
                                                  description=self.desc)
            self.arg_func(group, *args, **kwargs)
            parser._parse_known_args = self._enqueue_postprocessors(parser, parser._parse_known_args)
        
        def wrapper(target: SubCmd):
            if common:
                target.cmd_tree.register_common_args(target.name, _apply_group)
            else:
                _apply_group(target.parser)
            return target
        return wrapper

    def postprocessor(self, priority: int = 0):
        '''
        Adds a postprocessor function to the argument group.

        Args:
            func (NamespaceFunc): The postprocessor function to add.
            priority (int, optional): The priority of the postprocessor.

        Returns:
            Callable: The input function itself.
        '''
        def wrapper(func: NamespaceFunc):
            self.postprocessors.append((priority, func))
            return func
        return wrapper

    def _enqueue_postprocessors(self, obj, _parse_known_args_func):

        @wraps(_parse_known_args_func)
        def wrapper(*args, **kwargs):
            for priority, func in self.postprocessors:
                obj._cmd_tree.enqueue_postprocessor(func, priority)
            return _parse_known_args_func(*args, **kwargs)
        
        return wrapper


def arggroup(groupname: str | None = None,
             desc: str | None = None):
    def wrapper(adder_func: ArgAdderFunc):
        return ArgGroup(groupname, adder_func, desc=desc)
    return wrapper