#!/bin/bash

# 默认的 Elasticsearch 连接信息
DEFAULT_ES_HOST="http://localhost:9200"
DEFAULT_ES_USERNAME="elastic"
DEFAULT_ES_PASSWORD=""

# 解析命令行参数
ES_HOST="$DEFAULT_ES_HOST"
ES_USERNAME="$DEFAULT_ES_USERNAME"
ES_PASSWORD="$DEFAULT_ES_PASSWORD"

function show_usage {
  echo "用法: $0 [options]"
  echo "选项:"
  echo "  -h HOST      Elasticsearch 主机地址 (默认: $DEFAULT_ES_HOST)"
  echo "  -u USERNAME  Elasticsearch 用户名 (默认: $DEFAULT_ES_USERNAME)"
  echo "  -p PASSWORD  Elasticsearch 密码 (默认: $DEFAULT_ES_PASSWORD)"
  echo "  --help       显示此帮助信息"
  exit 1
}

while getopts ":h:u:p:-:" opt; do
  case $opt in
    h) ES_HOST="$OPTARG" ;;
    u) ES_USERNAME="$OPTARG" ;;
    p) ES_PASSWORD="$OPTARG" ;;
    -)
      case "${OPTARG}" in
        help) show_usage ;;
        *)
          echo "未知选项: --${OPTARG}" >&2
          show_usage
          ;;
      esac
      ;;
    \?)
      echo "未知选项: -$OPTARG" >&2
      show_usage
      ;;
    :)
      echo "选项 -$OPTARG 需要参数." >&2
      show_usage
      ;;
  esac
done

# 定义要删除的特定索引，这些是在es.py中定义的
INDICES=("business" "knowledge" "sqlcases" "prompt" "tableinfo" "settings" "synonym" "dim_values")

echo "使用以下连接信息:"
echo "主机: $ES_HOST"
echo "用户名: $ES_USERNAME"
echo "密码: ${ES_PASSWORD//?/*}"  # 屏蔽显示的密码
echo ""

echo "⚠️ 将要删除以下索引："
for index in "${INDICES[@]}"; do
  echo "$index"
done
echo ""
read -p "❓ 确定要删除这些索引吗？输入 yes 确认：" confirm

if [ "$confirm" == "yes" ]; then
  for index in "${INDICES[@]}"; do
    echo "🧨 删除索引: $index"
    curl -s -X DELETE -u "${ES_USERNAME}:${ES_PASSWORD}" "${ES_HOST}/${index}"
    echo ""
  done
  echo "✅ 所有指定索引已删除完成。"
else
  echo "❌ 已取消删除操作。"
fi