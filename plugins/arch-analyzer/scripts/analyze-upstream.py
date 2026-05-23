#!/usr/bin/env python3
"""
上游调用分析脚本

分析"谁在调用本服务"，基于 RPC Server 方法列表调用 xhs-tools MCP 查询上游。
此脚本生成查询参数和输出格式，实际 API 调用由 Claude Code 执行。

用法:
    # 生成查询任务
    python3 analyze-upstream.py <project-path> --generate-tasks

    # 从查询结果生成报告
    python3 analyze-upstream.py <project-path> --from-results <results.json>

输出:
    {project}/docs/rpc-analysis/{service}-upstream.json
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def resolve_project_path(path_or_name: str) -> Path:
    """解析项目路径"""
    if os.path.isdir(path_or_name):
        return Path(path_or_name)

    current_dir = Path.cwd()
    candidate = current_dir / path_or_name
    if candidate.is_dir():
        return candidate

    return Path(path_or_name)


def load_methods_data(project_path: Path) -> Optional[Dict]:
    """加载方法列表数据"""
    service_name = project_path.name
    methods_file = project_path / 'docs' / 'rpc-analysis' / f'{service_name}-methods.json'

    if methods_file.exists():
        with open(methods_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_xhs_project_config(service_name: str) -> Optional[str]:
    """尝试获取 xhs-tools 配置的 appName"""
    # 默认命名规则
    return f'{service_name}-service-default'


def generate_query_tasks(project_path: Path) -> Dict:
    """生成上游查询任务列表"""
    service_name = project_path.name
    methods_data = load_methods_data(project_path)

    if not methods_data:
        print(f"❌ 未找到方法列表，请先运行:")
        print(f"   python3 extract-rpc-methods.py {project_path}")
        return {}

    app_name = methods_data.get('appName', load_xhs_project_config(service_name))
    all_methods = methods_data.get('allMethods', [])

    tasks = {
        'project': service_name,
        'appName': app_name,
        'generatedAt': datetime.now().isoformat(),
        'totalMethods': len(all_methods),
        'queryTasks': []
    }

    for method in all_methods:
        tasks['queryTasks'].append({
            'method': method,
            'mcpTool': 'query_upstream_services',
            'params': {
                'app': app_name,
                'service': method,
                'days': 14
            }
        })

    return tasks


def print_query_commands(tasks: Dict):
    """打印 MCP 查询命令"""
    app_name = tasks.get('appName', '')
    query_tasks = tasks.get('queryTasks', [])

    print(f"\n{'=' * 60}")
    print(f"上游查询任务 - {tasks.get('project')}")
    print(f"{'=' * 60}")
    print(f"应用名: {app_name}")
    print(f"方法数: {len(query_tasks)}")
    print(f"\n需要对每个方法调用 xhs-tools MCP 的 query_upstream_services 工具:")
    print()

    # 只显示前 5 个示例
    for task in query_tasks[:5]:
        params = task['params']
        print(f"""mcp__plugin_xhs-tools_xhs-tools__query_upstream_services(
    app="{params['app']}",
    service="{params['service']}",
    days={params['days']}
)
""")

    if len(query_tasks) > 5:
        print(f"... 还有 {len(query_tasks) - 5} 个方法")


def process_upstream_results(project_path: Path, results: List[Dict]) -> Dict:
    """处理上游查询结果，生成报告"""
    service_name = project_path.name
    methods_data = load_methods_data(project_path)
    app_name = methods_data.get('appName') if methods_data else f'{service_name}-service-default'

    upstream_list = []
    methods_with_upstream = set()
    all_callers = set()

    for result in results:
        target_method = result.get('targetMethod', '')
        callers = result.get('callers', [])

        if callers:
            methods_with_upstream.add(target_method)

        for caller in callers:
            caller_app = caller.get('callerApp', '')
            all_callers.add(caller_app)

            upstream_list.append({
                'targetMethod': target_method,
                'callerApp': caller_app,
                'callerMethod': caller.get('callerMethod', ''),
                'calls': caller.get('calls', ''),
                'avgLatency': caller.get('avgLatency', ''),
                'maxLatency': caller.get('maxLatency', ''),
                'errorCount': caller.get('errorCount', 0)
            })

    # 按调用量排序
    def sort_key(x):
        calls = x.get('calls', '')
        if '亿' in str(calls):
            return 0
        elif '万' in str(calls):
            return 1
        elif str(calls).isdigit():
            return 2
        else:
            return 3

    upstream_list.sort(key=sort_key)

    # 统计 top callers
    caller_counts = {}
    for item in upstream_list:
        caller = item['callerApp']
        caller_counts[caller] = caller_counts.get(caller, 0) + 1

    top_callers = sorted(caller_counts.keys(), key=lambda x: caller_counts[x], reverse=True)[:5]

    total_methods = len(methods_data.get('allMethods', [])) if methods_data else 0

    return {
        'project': service_name,
        'analysisType': 'upstream',
        'analysisTime': datetime.now().isoformat(),
        'queryPeriod': '14 days',
        'appName': app_name,
        'upstream': upstream_list,
        'summary': {
            'totalMethods': total_methods,
            'methodsWithUpstream': len(methods_with_upstream),
            'totalCallers': len(all_callers),
            'topCallers': top_callers
        }
    }


def save_upstream_report(project_path: Path, report: Dict) -> str:
    """保存上游分析报告"""
    service_name = project_path.name
    output_dir = project_path / 'docs' / 'rpc-analysis'
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f'{service_name}-upstream.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return str(output_path)


def print_report_summary(report: Dict):
    """打印报告摘要"""
    summary = report.get('summary', {})
    upstream = report.get('upstream', [])

    print(f"\n{'=' * 60}")
    print(f"上游分析报告 - {report.get('project')}")
    print(f"{'=' * 60}")

    print(f"\n📊 统计:")
    print(f"  • 分析方法数: {summary.get('totalMethods', 0)}")
    print(f"  • 有上游调用: {summary.get('methodsWithUpstream', 0)}")
    print(f"  • 上游调用方: {summary.get('totalCallers', 0)}")

    if summary.get('topCallers'):
        print(f"\n🔥 主要调用方:")
        for caller in summary['topCallers']:
            print(f"  • {caller}")

    if upstream:
        print(f"\n📈 高频上游 TOP 5:")
        for item in upstream[:5]:
            print(f"  • {item['callerApp']}.{item['callerMethod']} → {item['targetMethod']}: {item['calls']}")


def main():
    parser = argparse.ArgumentParser(description='上游调用分析工具')
    parser.add_argument('project_path', help='项目路径')
    parser.add_argument('--generate-tasks', '-g', action='store_true',
                        help='生成查询任务列表')
    parser.add_argument('--from-results', '-r', type=str,
                        help='从结果文件生成报告')
    parser.add_argument('--output', '-o', help='输出文件路径')

    args = parser.parse_args()

    project_path = resolve_project_path(args.project_path)

    if not project_path.is_dir():
        print(f"❌ 项目路径不存在: {args.project_path}")
        return 1

    if args.generate_tasks:
        # 生成查询任务
        tasks = generate_query_tasks(project_path)
        if tasks:
            print_query_commands(tasks)

            # 保存任务文件
            task_file = project_path / 'docs' / 'rpc-analysis' / f'{project_path.name}-upstream-tasks.json'
            task_file.parent.mkdir(parents=True, exist_ok=True)
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 任务文件已保存: {task_file}")

    elif args.from_results:
        # 从结果生成报告
        with open(args.from_results, 'r', encoding='utf-8') as f:
            results = json.load(f)

        report = process_upstream_results(project_path, results)
        output_path = save_upstream_report(project_path, report)
        print_report_summary(report)
        print(f"\n✅ 报告已保存: {output_path}")

    else:
        # 默认：显示使用说明
        print("""
上游分析工具使用说明:

1. 生成查询任务:
   python3 analyze-upstream.py <project> --generate-tasks

2. 使用 Claude Code 执行 xhs-tools MCP 查询

3. 从结果生成报告:
   python3 analyze-upstream.py <project> --from-results <results.json>

或者直接使用 Claude Code 自动执行整个流程。
""")

    return 0


if __name__ == '__main__':
    exit(main())
