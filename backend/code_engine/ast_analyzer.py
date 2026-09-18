import ast
from pathlib import PurePosixPath

def analyze(path: str, source: str):
    out = {'symbols': [], 'imports': [], 'calls': [], 'inherits': [], 'errors': []}
    if path.endswith('.py'):
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            out['errors'].append(f'{path}:{e.lineno}: {e.msg}'); return out
        class Visitor(ast.NodeVisitor):
            stack = []
            def definition(self, node):
                name = '.'.join(self.stack + [node.name])
                out['symbols'].append({'id': f'{path}::{name}', 'name': name, 'kind': 'class' if isinstance(node, ast.ClassDef) else 'function', 'line': node.lineno, 'end': node.end_lineno, 'path': path})
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        out['inherits'].append({'source': f'{path}::{name}', 'target': ast.unparse(base)})
                self.stack.append(node.name); self.generic_visit(node); self.stack.pop()
            visit_FunctionDef = definition
            visit_AsyncFunctionDef = definition
            visit_ClassDef = definition
            def visit_Import(self, node):
                out['imports'].extend(a.name for a in node.names)
            def visit_ImportFrom(self, node):
                out['imports'].append('.' * node.level + (node.module or ''))
                for a in node.names:
                    out['imports'].append('.' * node.level + '.'.join(filter(None, [node.module, a.name])))
            def visit_Call(self, node):
                out['calls'].append({'source': f"{path}::{'.'.join(self.stack)}" if self.stack else path, 'target': ast.unparse(node.func), 'line': node.lineno})
                self.generic_visit(node)
        Visitor().visit(tree)
    elif PurePosixPath(path).suffix in {'.js', '.jsx', '.ts', '.tsx'}:
        from tree_sitter import Language, Parser
        if path.endswith(('.ts', '.tsx')):
            import tree_sitter_typescript as lang
            language = Language(lang.language_tsx() if path.endswith('.tsx') else lang.language_typescript())
        else:
            import tree_sitter_javascript as lang
            language = Language(lang.language())
        tree = Parser(language).parse(source.encode())
        if tree.root_node.has_error:
            out['errors'].append(f'{path}: Tree-sitter found parse errors')
        def walk(node, owner=path):
            if node.type in {'function_declaration', 'class_declaration', 'method_definition'}:
                n = node.child_by_field_name('name')
                if n:
                    name = n.text.decode(); owner = f'{path}::{name}:{node.start_point.row+1}'
                    out['symbols'].append({'id': owner, 'name': name, 'path': path, 'kind': 'class' if 'class' in node.type else 'function', 'line': node.start_point.row+1, 'end': node.end_point.row+1})
            if node.type == 'import_statement':
                n = node.child_by_field_name('source')
                if n: out['imports'].append(n.text.decode().strip('\"\''))
            if node.type == 'call_expression':
                n = node.child_by_field_name('function')
                if n: out['calls'].append({'source': owner, 'target': n.text.decode(), 'line': node.start_point.row+1})
            for child in node.children: walk(child, owner)
        walk(tree.root_node)
    return out
