#!/usr/bin/env python3
"""
增强版 RPC 依赖分析脚本

改进点：
1. 支持多种 RPC 调用模式识别
2. 支持 MQ 生产者/消费者分析
3. 支持数据库表依赖分析
4. 输出更丰富的依赖元信息
5. 方法级调用追踪

用法:
    # 使用服务名（自动在当前目录查找）
    python3 analyze-rpc-enhanced.py redsettlement

    # 使用完整路径
    python3 analyze-rpc-enhanced.py /path/to/redsettlement

    # 指定输出文件
    python3 analyze-rpc-enhanced.py redsettlement --output docs/rpc-analysis/redsettlement-enhanced.json
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


class EnhancedRpcAnalyzer:
    """增强版 RPC 依赖分析器"""

    # RPC 调用模式
    RPC_PATTERNS = [
        # 模式 1: ClientBuilder.create(XxxService.Iface.class, "service-name")
        (r'ClientBuilder\.create\s*\(\s*([A-Za-z0-9_]+)\.Iface\.class\s*,\s*"([^"]+)"',
         'ClientBuilder.create', lambda m: (m.group(1), m.group(2))),

        # 模式 2: @Resource 注入
        (r'@Resource[^\n]*\n\s*private\s+([A-Za-z0-9_]+)\.Iface\s+(\w+)\s*;',
         '@Resource injection', lambda m: (m.group(1), None)),

        # 模式 3: @Autowired 注入
        (r'@Autowired[^\n]*\n\s*private\s+([A-Za-z0-9_]+)\.Iface\s+(\w+)\s*;',
         '@Autowired injection', lambda m: (m.group(1), None)),
    ]

    # MQ 生产者模式
    MQ_PRODUCER_PATTERNS = [
        # Events.sendAsync / Events.send
        (r'Events\.(sendAsync|send)\s*\(\s*"([^"]+)"',
         'Events.send', lambda m: m.group(2)),

        # eventProducer.send
        (r'eventProducer\.send\s*\([^,]*,\s*"([^"]+)"',
         'EventProducer', lambda m: m.group(1)),

        # @EventsTopic 注解
        (r'@EventsTopic\s*\(\s*"([^"]+)"',
         '@EventsTopic', lambda m: m.group(1)),

        # AbstractProducer 子类的 getTopic 方法（小红书内部模式）
        (r'return\s*"([^"]+_[^"]+)";\s*$',
         'AbstractProducer.getTopic', lambda m: m.group(1)),
    ]

    # MQ 消费者模式
    MQ_CONSUMER_PATTERNS = [
        # @EventListener
        (r'@EventListener\s*\([^)]*topic\s*=\s*"([^"]+)"',
         '@EventListener', lambda m: m.group(1)),

        # @RocketMQMessageListener
        (r'@RocketMQMessageListener\s*\([^)]*topic\s*=\s*"([^"]+)"',
         '@RocketMQMessageListener', lambda m: m.group(1)),
    ]

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name

    def find_java_files(self, pattern: str = '**/*.java') -> List[Path]:
        """查找所有 Java 文件"""
        return list(self.project_path.glob(pattern))

    def analyze_rpc_dependencies(self) -> Tuple[List[Dict], List[Dict]]:
        """
        分析 RPC 依赖
        返回: (bean_definitions, usage_points)
        - bean_definitions: ClientBuilder.create 定义的 Bean
        - usage_points: @Resource/@Autowired 注入的使用点
        """
        bean_definitions = []  # Bean 定义（有服务名）
        usage_points = []      # 使用点（无服务名，仅接口）
        seen_beans = set()
        seen_usages = set()

        for java_file in self.find_java_files():
            try:
                content = java_file.read_text(encoding='utf-8')
                # 移除注释
                content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

                for pattern, pattern_name, extractor in self.RPC_PATTERNS:
                    for match in re.finditer(pattern, content, re.DOTALL):
                        interface_class, service_name = extractor(match)

                        if service_name:
                            # 这是 Bean 定义（ClientBuilder.create）
                            key = (interface_class, service_name)
                            if key not in seen_beans:
                                seen_beans.add(key)
                                target_app = self._extract_target_app(service_name)
                                bean_definitions.append({
                                    'type': 'RPC',
                                    'interfaceClass': f'{interface_class}.Iface',
                                    'serviceName': service_name,
                                    'targetApp': target_app,
                                    'pattern': pattern_name,
                                    'sourceFile': str(java_file.relative_to(self.project_path))
                                })
                        else:
                            # 这是使用点（@Resource/@Autowired 注入）
                            key = (interface_class, str(java_file))
                            if key not in seen_usages:
                                seen_usages.add(key)
                                usage_points.append({
                                    'interfaceClass': f'{interface_class}.Iface',
                                    'pattern': pattern_name,
                                    'sourceFile': str(java_file.relative_to(self.project_path))
                                })
            except Exception as e:
                print(f"警告: 无法处理文件 {java_file}: {e}")

        return (
            sorted(bean_definitions, key=lambda x: (x['targetApp'], x['interfaceClass'])),
            sorted(usage_points, key=lambda x: x['interfaceClass'])
        )

    def analyze_mq_producers(self) -> List[Dict]:
        """分析 MQ 生产者"""
        producers = []
        seen = set()

        for java_file in self.find_java_files():
            try:
                content = java_file.read_text(encoding='utf-8')
                original_content = content  # 保留原始内容用于类继承检查
                content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

                # 检查是否是 AbstractProducer 子类
                is_producer_class = 'extends AbstractProducer' in original_content

                for pattern, pattern_name, extractor in self.MQ_PRODUCER_PATTERNS:
                    # AbstractProducer.getTopic 模式只在 Producer 类中匹配
                    if pattern_name == 'AbstractProducer.getTopic' and not is_producer_class:
                        continue

                    for match in re.finditer(pattern, content, re.MULTILINE):
                        topic = extractor(match)
                        # 过滤掉明显不是 topic 的返回值
                        if topic and topic not in seen and '_' in topic:
                            seen.add(topic)
                            producers.append({
                                'type': 'MQ_PRODUCER',
                                'topic': topic,
                                'pattern': pattern_name,
                                'sourceFile': str(java_file.relative_to(self.project_path))
                            })
            except Exception:
                pass

        return sorted(producers, key=lambda x: x['topic'])

    def analyze_mq_consumers(self) -> List[Dict]:
        """分析 MQ 消费者"""
        consumers = []
        seen = set()

        for java_file in self.find_java_files():
            try:
                content = java_file.read_text(encoding='utf-8')
                content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

                for pattern, pattern_name, extractor in self.MQ_CONSUMER_PATTERNS:
                    for match in re.finditer(pattern, content):
                        topic = extractor(match)
                        if topic and topic not in seen:
                            seen.add(topic)
                            consumers.append({
                                'type': 'MQ_CONSUMER',
                                'topic': topic,
                                'pattern': pattern_name,
                                'sourceFile': str(java_file.relative_to(self.project_path))
                            })
            except Exception:
                pass

        return sorted(consumers, key=lambda x: x['topic'])

    def analyze_database_tables(self) -> List[Dict]:
        """分析数据库表依赖（从 Mapper 接口提取）"""
        tables = []
        seen = set()

        # 查找 Mapper XML 文件
        for xml_file in self.project_path.glob('**/*Mapper.xml'):
            try:
                content = xml_file.read_text(encoding='utf-8')
                # 提取表名
                table_pattern = r'(?:from|into|update|join)\s+`?(\w+)`?'
                for match in re.finditer(table_pattern, content, re.IGNORECASE):
                    table = match.group(1).lower()
                    if table not in seen and not table.startswith('dual'):
                        seen.add(table)
                        tables.append({
                            'type': 'DATABASE',
                            'table': table,
                            'sourceFile': str(xml_file.relative_to(self.project_path))
                        })
            except Exception:
                pass

        return sorted(tables, key=lambda x: x['table'])

    def analyze_rpc_actual_calls(self, rpc_beans: List[Dict]) -> Dict[str, Dict]:
        """
        分析 RPC 接口的实际调用情况
        基于 Bean 定义，搜索代码中对该接口方法的调用
        """
        call_analysis = {}

        for bean in rpc_beans:
            interface_name = bean['interfaceClass'].replace('.Iface', '')
            # 构造可能的变量名（驼峰命名）
            var_name = interface_name[0].lower() + interface_name[1:]

            # 搜索 main 代码中的调用
            call_pattern = f'{var_name}\\.'
            call_files = []

            for java_file in self.project_path.glob('**/src/main/**/*.java'):
                try:
                    content = java_file.read_text(encoding='utf-8')
                    if re.search(call_pattern, content):
                        # 提取调用的方法（支持方法名后有空格的情况）
                        methods = re.findall(rf'{var_name}\.([a-zA-Z0-9_]+)\s*\(', content, re.MULTILINE)
                        call_files.append({
                            'file': str(java_file.relative_to(self.project_path)),
                            'methods': list(set(methods))
                        })
                except Exception:
                    pass

            call_analysis[interface_name] = {
                'hasMainCalls': len(call_files) > 0,
                'callCount': len(call_files),
                'callLocations': call_files
            }

        return call_analysis

    def _extract_target_app(self, service_name: str) -> str:
        """从服务名提取目标应用"""
        if not service_name:
            return 'unknown'
        if '-service-' in service_name:
            return service_name.split('-service-')[0]
        return service_name

    def run_full_analysis(self) -> Dict:
        """运行完整分析"""
        rpc_beans, rpc_usages = self.analyze_rpc_dependencies()
        mq_producers = self.analyze_mq_producers()
        mq_consumers = self.analyze_mq_consumers()
        db_tables = self.analyze_database_tables()

        # 统计目标应用（仅从 Bean 定义统计，避免重复）
        rpc_apps = {}
        for dep in rpc_beans:
            app = dep['targetApp']
            rpc_apps[app] = rpc_apps.get(app, 0) + 1

        # 关联使用点到 Bean 定义
        interface_to_usages = {}
        for usage in rpc_usages:
            iface = usage['interfaceClass']
            if iface not in interface_to_usages:
                interface_to_usages[iface] = []
            interface_to_usages[iface].append(usage['sourceFile'])

        # 为每个 Bean 添加使用点信息
        for bean in rpc_beans:
            iface = bean['interfaceClass']
            bean['usagePoints'] = interface_to_usages.get(iface, [])
            bean['usageCount'] = len(bean['usagePoints'])

        # 分析实际调用情况
        call_analysis = self.analyze_rpc_actual_calls(rpc_beans)

        # 合并调用分析结果到 Bean
        unused_count = 0
        for bean in rpc_beans:
            interface_name = bean['interfaceClass'].replace('.Iface', '')
            call_info = call_analysis.get(interface_name, {})
            bean['hasMainCalls'] = call_info.get('hasMainCalls', False)
            bean['callLocations'] = call_info.get('callLocations', [])
            if not bean['hasMainCalls']:
                unused_count += 1

        return {
            'project': self.project_name,
            'projectPath': str(self.project_path.absolute()),
            'analysisType': 'static-enhanced',
            'analysisTime': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'summary': {
                'rpcBeanDefinitions': len(rpc_beans),
                'rpcUsagePoints': len(rpc_usages),
                'rpcUnusedBeans': unused_count,
                'uniqueRpcApps': len(rpc_apps),
                'mqProducers': len(mq_producers),
                'mqConsumers': len(mq_consumers),
                'databaseTables': len(db_tables)
            },
            'rpcAppSummary': rpc_apps,
            'rpcDependencies': rpc_beans,
            'rpcUsageDetails': rpc_usages,
            'mqProducers': mq_producers,
            'mqConsumers': mq_consumers,
            'databaseTables': db_tables
        }


def print_summary(result: Dict):
    """打印分析摘要"""
    print("\n" + "=" * 60)
    print(f"增强版依赖分析报告 - {result['project']}")
    print("=" * 60)

    summary = result['summary']
    print(f"\n📊 分析摘要:")
    print(f"  • RPC Bean 定义: {summary['rpcBeanDefinitions']} 个 ({summary['uniqueRpcApps']} 个目标服务)")
    print(f"  • RPC 使用点: {summary['rpcUsagePoints']} 个")
    print(f"  • RPC 未调用: {summary['rpcUnusedBeans']} 个 ⚠️" if summary['rpcUnusedBeans'] > 0 else f"  • RPC 未调用: 0 个 ✅")
    print(f"  • MQ 生产者: {summary['mqProducers']} 个")
    print(f"  • MQ 消费者: {summary['mqConsumers']} 个")
    print(f"  • 数据库表: {summary['databaseTables']} 个")

    if result['rpcAppSummary']:
        print(f"\n🔗 RPC 目标服务分布:")
        for app, count in sorted(result['rpcAppSummary'].items()):
            print(f"  • {app}: {count} 个接口")

    # 显示使用频率最高的接口
    deps_with_usage = [d for d in result['rpcDependencies'] if d.get('usageCount', 0) > 0]
    if deps_with_usage:
        print(f"\n📍 接口使用频率 TOP 5:")
        sorted_deps = sorted(deps_with_usage, key=lambda x: x['usageCount'], reverse=True)[:5]
        for dep in sorted_deps:
            print(f"  • {dep['interfaceClass']}: {dep['usageCount']} 处使用")

    # 显示未使用的接口
    unused_beans = [d for d in result['rpcDependencies'] if not d.get('hasMainCalls', True)]
    if unused_beans:
        print(f"\n⚠️ 未调用的 RPC 接口 ({len(unused_beans)} 个):")
        for bean in unused_beans:
            print(f"  • {bean['interfaceClass']} → {bean['targetApp']}")

    if result['mqProducers']:
        print(f"\n📤 MQ 生产者 Topic:")
        for p in result['mqProducers']:
            print(f"  • {p['topic']}")

    if result['mqConsumers']:
        print(f"\n📥 MQ 消费者 Topic:")
        for c in result['mqConsumers']:
            print(f"  • {c['topic']}")


def resolve_project_path(path_or_name: str) -> str:
    """解析项目路径，支持服务名或完整路径"""
    # 如果是完整路径且存在
    if os.path.isdir(path_or_name):
        return path_or_name

    # 尝试作为服务名在当前目录查找
    current_dir = Path.cwd()
    candidate = current_dir / path_or_name
    if candidate.is_dir():
        return str(candidate)

    # 尝试在脚本所在目录的上级目录查找（假设脚本在 docs/scripts 下）
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    candidate = repo_root / path_or_name
    if candidate.is_dir():
        return str(candidate)

    return path_or_name  # 返回原值，让后续检查失败


def get_default_output_path(project_path: Path, project_name: str) -> str:
    """获取默认输出路径（输出到项目目录下）"""
    output_dir = project_path / 'docs' / 'rpc-analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir / f'{project_name}-enhanced.json')


def main():
    parser = argparse.ArgumentParser(description='增强版 RPC 依赖分析工具')
    parser.add_argument('project_path', help='项目路径或服务名（如 redsettlement）')
    parser.add_argument('--output', '-o', default=None,
                        help='输出 JSON 文件路径（默认: docs/rpc-analysis/<service>-enhanced.json）')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='静默模式，只输出 JSON')

    args = parser.parse_args()

    # 解析项目路径
    project_path = resolve_project_path(args.project_path)

    if not os.path.isdir(project_path):
        print(f"错误: 项目路径不存在: {args.project_path}")
        print(f"提示: 请确保在 RedPay 仓库根目录运行，或提供完整路径")
        return 1

    analyzer = EnhancedRpcAnalyzer(project_path)

    # 确定输出路径（输出到项目目录下的 docs/rpc-analysis/）
    output_path = args.output or get_default_output_path(Path(project_path), analyzer.project_name)

    result = analyzer.run_full_analysis()

    # 确保输出目录存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存 JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if not args.quiet:
        print_summary(result)
        print(f"\n✅ JSON 输出已保存到: {output_path}")

    return 0


if __name__ == '__main__':
    exit(main())
