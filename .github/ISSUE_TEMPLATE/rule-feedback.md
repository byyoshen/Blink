---
name: 规则漏网反馈
about: 提交代理日志确认的漏网域名（需附证据；仅供维护者评估，不构成修改承诺）
title: "[漏网] <App 名称> - <域名>"
body:
  - type: markdown
    attributes:
      value: |
        谢谢反馈。本仓库是个人维护项目：**只评估带证据的反馈**，无证据的"不行了"类问题不会被处理。
        反馈前请先自检：① 策略与顺序设置（规则集本身不带策略）；② 目标是否属于
        Reject / Domestic / CDN / China IP / LAN 等基础设施（仓库有意不收录）。
  - type: input
    id: client
    attributes:
      label: 你使用的客户端
      placeholder: Surge / Shadowrocket / Loon / Stash / mihomo / Egern / Quantumult X
    validations:
      required: true
  - type: input
    id: app
    attributes:
      label: 属于哪个 App（不确定请填"待确认"）
      placeholder: 例：YouTube
    validations:
      required: true
  - type: input
    id: domain
    attributes:
      label: 漏网域名 / 主机名（来自代理日志）
      placeholder: 例：cdn-xxx.example.com
    validations:
      required: true
  - type: textarea
    id: evidence
    attributes:
      label: 日志证据
      description: 粘贴代理客户端日志中该域名的命中 / 等待 / 超时相关片段。不提供日志证据的反馈将不会被处理。
      render: text
    validations:
      required: true
  - type: input
    id: upstream
    attributes:
      label: 与选定上游的比较结果
      description: 该域名是否存在于该 App 的 primary 上游？（可附上游 URL）。只有确认上游缺失的才会被评估补充。
    validations:
      required: true
  - type: dropdown
    id: expectation
    attributes:
      label: 期望处置
      options:
        - 纳入 supplement（需日志确认缺口）
        - 调整 primary 上游（需 source audit）
        - 仅告知，无需变更
    validations:
      required: true
  - type: checkboxes
    id: agreement
    attributes:
      label: 确认
      options:
        - label: 已阅读 DISCLAIMER 与 THIRD_PARTY_NOTICES；同意本仓库仅依据证据由维护者评估采纳，不保证响应时间与结果
          required: true
