import { useState } from "react";

export default function HelpGuide() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        className="help-btn"
        onClick={() => setOpen(true)}
        aria-label="平台指南"
        title="平台指南"
      >
        ?
      </button>

      {open && (
        <div className="help-overlay" onClick={() => setOpen(false)}>
          <div className="help-panel" onClick={(e) => e.stopPropagation()}>
            <header className="help-head">
              <h2>平台指南</h2>
              <button className="help-close" onClick={() => setOpen(false)} aria-label="关闭">
                ×
              </button>
            </header>

            <div className="help-body">
              <section>
                <h3>平台简介</h3>
                <p>
                  AutoGrader 将「一次不可追溯的模型打分」改造为
                  <b> 可检查、可修正、可回放</b> 的实验报告评阅流程。
                  AI 只提供循证建议，最终成绩由教师复核后发布。
                </p>
              </section>

              <section>
                <h3>教师工作流</h3>
                <ol className="help-steps">
                  <li>新建课程（课程名 / 编号 / 学期）</li>
                  <li>进入课程，新建作业</li>
                  <li>在「评分量表」页从模板创建量表（排序实验 / 最短路径）</li>
                  <li>在作业下上传学生报告（PDF / Markdown）</li>
                  <li>点击「发起评阅」——系统自动解析并循证评阅</li>
                  <li>进入三栏评阅台，逐项复核并定档</li>
                  <li>点击「发布成绩」，学生即可查看</li>
                </ol>
              </section>

              <section>
                <h3>三栏评阅台</h3>
                <ul className="help-list">
                  <li>
                    <b>左栏</b> — 评分项清单，显示每项证据状态与待复核标记
                  </li>
                  <li>
                    <b>中栏</b> — 报告原文，<mark>琥珀色高亮</mark>为模型引用的证据
                  </li>
                  <li>
                    <b>右栏</b> — 模型建议（状态 / 档位 / 解释）+ 人工决定（点选档位 + 反馈）
                  </li>
                </ul>
              </section>

              <section>
                <h3>循证评阅与证据状态</h3>
                <ul className="help-list">
                  <li>
                    <span className="badge supported">有证据支持</span> — 报告中有明确原文证据
                  </li>
                  <li>
                    <span className="badge missing">内容缺失</span> — 报告缺该项要求的内容
                  </li>
                  <li>
                    <span className="badge uncertain">无法确定</span> — 证据含糊，需人工判断
                  </li>
                  <li>
                    <span className="badge needs_review">待复核</span> — 证据不足 / 解析不全 / 内容矛盾 /
                    模型不确定时，系统<b>不会自动判零分</b>，而是交人工复核
                  </li>
                </ul>
              </section>

              <section>
                <h3>矛盾检测</h3>
                <p>
                  系统自动检测表格中的数值矛盾（如数据规模递增、运行时间却反常下降），并在评阅台顶部给出告警。
                </p>
              </section>

              <section>
                <h3>学生工作流</h3>
                <p>
                  注册登录后，在课程作业下查看<b>已发布成绩</b>与逐项档位反馈。
                  修订版上传后，教师可在「版本对比」中查看修订前后的内容与分数变化。
                </p>
              </section>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
