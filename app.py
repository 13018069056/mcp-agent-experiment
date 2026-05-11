import gradio as gr
import json
import os
import time
import csv
import tempfile
from openai import OpenAI

client = OpenAI(base_url='http://localhost:11434/v1', api_key='local', timeout=120)

mock_employees = [
    {"id": "E01", "name": "张三", "level": "L1"},
    {"id": "E02", "name": "李四", "level": "L2"},
    {"id": "E03", "name": "王五", "level": "L3"}
]
mock_salary_levels = {"L1": 10000, "L2": 20000, "L3": 35000}

def get_employee_directory():
    return json.dumps(mock_employees, ensure_ascii=False)

def calculate_payroll_and_tax(employees_json: str):
    employees = json.loads(employees_json)
    res = []
    for emp in employees:
        base = mock_salary_levels[emp["level"]]
        social = base * 0.2
        tax = max(0, (base - social) * 0.05)
        net = base - social - tax
        emp.update({"应发工资": base, "五险一金扣除": social, "个税扣除": tax, "实发工资": net})
        res.append(emp)
    return json.dumps(res, ensure_ascii=False)

def export_payroll_csv(payroll_json: str):
    data = json.loads(payroll_json)
    path = os.path.join(tempfile.gettempdir(), "payroll_report.csv")
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, data[0].keys())
        w.writeheader()
        w.writerows(data)
    return json.dumps({"status":"success","file_path":path}, ensure_ascii=False)

def saas_generate_payroll_api():
    time.sleep(1)
    emp = get_employee_directory()
    payroll = calculate_payroll_and_tax(emp)
    file_info = json.loads(export_payroll_csv(payroll))
    table = [[d["name"], d["level"], d["应发工资"], d["五险一金扣除"], d["实发工资"]] for d in json.loads(payroll)]
    return table, file_info["file_path"]

tools_schema = [
    {"type":"function","function":{"name":"get_employee_directory","description":"获取全公司员工花名册"}},
    {"type":"function","function":{"name":"calculate_payroll_and_tax","description":"计算工资、五险一金、个税","parameters":{"type":"object","properties":{"employees_json":{"type":"string"}},"required":["employees_json"]}}},
    {"type":"function","function":{"name":"export_payroll_csv","description":"导出工资CSV文件","parameters":{"type":"object","properties":{"payroll_json":{"type":"string"}},"required":["payroll_json"]}}}
]

def agent_orchestrator(user_msg, history, msg_state, model):
    history = history or []
    msg_state = msg_state or []
    if not msg_state:
        msg_state = [{"role":"system","content":"自动调用工具：查员工→算工资→导出CSV，最后用表格输出结果"}]
    msg_state.append({"role":"user","content":user_msg})
    history += [{"role":"user","content":user_msg},{"role":"assistant","content":f"🤖 正在使用 {model} 规划任务..."}]
    yield history, msg_state
    for _ in range(10):
        resp = client.chat.completions.create(model=model, messages=msg_state, tools=tools_schema, tool_choice="auto")
        msg = resp.choices[0].message
        msg_state.append(msg.model_dump())
        if msg.tool_calls:
            for call in msg.tool_calls:
                func = call.function.name
                args = json.loads(call.function.arguments or "{}")
                history[-1]["content"] += f"\n🛠️ 执行工具：{func}"
                yield history, msg_state
                if func == "get_employee_directory":
                    res = get_employee_directory()
                elif func == "calculate_payroll_and_tax":
                    res = calculate_payroll_and_tax(args["employees_json"])
                elif func == "export_payroll_csv":
                    res = export_payroll_csv(args["payroll_json"])
                else:
                    res = json.dumps({"error":"未知工具"})
                msg_state.append({"role":"tool","tool_call_id":call.id,"name":func,"content":res})
            continue
        history[-1]["content"] = msg.content
        yield history, msg_state
        break

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# SaaS vs AI‑Agent(MCP) 对比实验")
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🏢 传统SaaS（固定流程）")
            btn = gr.Button("一键生成工资单", variant="primary")
            table = gr.Dataframe(headers=["姓名","职级","应发工资","五险一金","实发工资"])
            file = gr.File(label="下载CSV文件")
            btn.click(saas_generate_payroll_api, outputs=[table, file])
        with gr.Column():
            gr.Markdown("### 🤖 AI‑Agent（MCP智能调用）")
            model_sel = gr.Dropdown(["qwen3.6:27b","qwen3.6:35b‑a3b"], value="qwen3.6:35b‑a3b", label="选择模型")
            state = gr.State([])
            chat = gr.Chatbot(height=450)
            txt = gr.Textbox(placeholder="输入指令：帮我查询员工、计算工资、导出CSV")
            txt.submit(agent_orchestrator, inputs=[txt, chat, state, model_sel], outputs=[chat, state])

demo.launch()
