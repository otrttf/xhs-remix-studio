const notes = [
  {
    title: "北京胡同里这家小馆，饭点真的坐满",
    author: "北漂吃饭记录",
    likes: "1,024",
    body: "这家在胡同边的小馆很适合朋友聚餐。菜量扎实，价格不虚，招牌菜是热乎乎端上来的，适合想吃点真实北京味的人。",
    tags: ["北京美食", "胡同小馆", "朋友聚餐"],
  },
  {
    title: "学生党也能吃好的北京烤鸭路线",
    author: "周末探店员",
    likes: "768",
    body: "这条路线适合预算有限但又想认真吃一顿的人。避开太游客的点，保留仪式感，也能吃到靠谱的烤鸭和小菜。",
    tags: ["北京烤鸭", "学生党", "本地生活"],
  },
  {
    title: "北京火锅清单，适合下班后直接冲",
    author: "不想做饭研究所",
    likes: "1,536",
    body: "整理了几家适合下班后吃的火锅店。有的适合热闹聚餐，有的适合两个人慢慢吃，重点是排队和预算都比较可控。",
    tags: ["北京火锅", "下班吃什么", "聚餐"],
  },
  {
    title: "周末去吃的烤肉店，适合三五好友",
    author: "周末饭局备忘录",
    likes: "2,018",
    body: "店里烟火气很足，烤肉分量比较实在，适合朋友一起去。人多时点套餐更划算，首图适合放烤盘近景。",
    tags: ["北京烤肉", "周末聚餐", "朋友饭局"],
  },
];

const personas = {
  xiaobai: {
    name: "小白",
    description: "00后女大学生，语言生动活泼，喜欢用真实体验、轻松吐槽和口语化表达分享好吃好玩的东西。",
    rules: [
      "开头先给一个情绪钩子，让人马上知道这家店值不值得冲。",
      "融入个人真实身份标签（如“学生党”“00后”）增强代入感和可信度。",
      "整体文风保持“真实体验分享者”而非“专业推荐者”的平等对话语气。",
      "人设写作应保持第一人称视角、emoji点缀、口语化感叹词等特征贯穿全文。",
      "标题要有小白的活泼感，但不要总用“救命”开头；多用场景、反差、真实感和馋感来制造吸引力。",
    ],
    rewrite(note) {
      const food = note.title.includes("烤鸭") ? "烤鸭" : note.title.includes("火锅") ? "火锅" : "北京小店";
      return {
        title: `${food}这条我真的会存，学生党和朋友聚餐都能冲`,
        body: `谁懂啊，我一开始只是想找个不踩雷的吃饭地方，结果这条素材越看越适合二创成探店笔记。\n\n${note.body}\n\n我会把重点放在“真实体验”上：不是硬夸它多网红，而是告诉大家什么场景适合去、预算大概怎么想、朋友来北京能不能带过去。这样写会更像一个真的吃过的人在分享，而不是冷冰冰的推荐清单。\n\n如果发小红书，我会用首图抓住食欲，中间放环境和菜品细节，最后补一点价格/排队信息，可信度会更高。`,
        tags: note.tags.concat(["小白探店", "真实体验", "学生党美食"]),
      };
    },
  },
  xiaohei: {
    name: "小黑",
    description: "初入职场的打工人，性别男，爱玩游戏，喜欢麻辣。语言简洁客观。",
    rules: [
      "先给结论，再写适合场景。",
      "表达简洁，不堆太多情绪词。",
      "重点说明口味、分量、排队和性价比。",
      "可以保留一点打工人视角，比如下班后、周末、朋友局。",
    ],
    rewrite(note) {
      return {
        title: `${note.title}，适合下班后直接去`,
        body: `结论：这条素材适合改成一篇偏实用的北京美食笔记。\n\n${note.body}\n\n如果按“小黑”的口吻写，我会少用夸张表达，重点写清楚三件事：味道稳不稳、适合几个人去、价格和排队是否能接受。对上班族来说，最重要的是下班后不用做太多功课，看完就知道值不值得去。\n\n图片建议保留菜品近景和环境图，少放纯氛围图，多给决策信息。`,
        tags: note.tags.concat(["下班吃什么", "打工人探店", "实用推荐"]),
      };
    },
  },
};

let activeNoteIndex = 0;
let activePersonaKey = "xiaobai";
let drafts = [];

const noteList = document.querySelector("#noteList");
const personaList = document.querySelector("#personaList");
const sourceTitle = document.querySelector("#sourceTitle");
const sourceMeta = document.querySelector("#sourceMeta");
const sourceBody = document.querySelector("#sourceBody");
const draftTitle = document.querySelector("#draftTitle");
const draftBody = document.querySelector("#draftBody");
const tagRow = document.querySelector("#tagRow");
const ruleList = document.querySelector("#ruleList");
const draftList = document.querySelector("#draftList");
const personaName = document.querySelector("#personaName");
const personaDescription = document.querySelector("#personaDescription");
const newRuleInput = document.querySelector("#newRuleInput");
const currentNoteName = document.querySelector("#currentNoteName");
const currentPersonaName = document.querySelector("#currentPersonaName");
const keywordInput = document.querySelector("#keyword");
const collectCountInput = document.querySelector("#collectCount");
const collectStatus = document.querySelector("#collectStatus");
const ruleStatus = document.querySelector("#ruleStatus");
const summaryCount = document.querySelector("#summaryCount");
const summaryKeywords = document.querySelector("#summaryKeywords");
const summaryLatest = document.querySelector("#summaryLatest");

function renderPersonas() {
  personaList.innerHTML = Object.entries(personas)
    .map(([key, persona]) => `
      <button class="persona-card ${key === activePersonaKey ? "active" : ""}" data-persona="${key}" type="button">
        <strong>${persona.name}</strong>
        <small>${persona.description}</small>
      </button>
    `)
    .join("");
}

function renderNotes() {
  noteList.innerHTML = notes
    .map((note, index) => `
      <button class="note-card ${index === activeNoteIndex ? "active" : ""}" data-note="${index}" type="button">
        <span class="thumb"></span>
        <span>
          <strong>${note.title}</strong>
          <small>${note.author} · ${note.likes} 赞 · ok</small>
        </span>
      </button>
    `)
    .join("");
}

function renderPersonaDetail() {
  const persona = personas[activePersonaKey];
  personaName.textContent = persona.name;
  personaDescription.value = persona.description;
  currentPersonaName.textContent = persona.name;
  ruleList.innerHTML = persona.rules
    .map((rule, index) => `
      <li>
        <span>${rule}</span>
        <button class="delete-rule" data-rule="${index}" type="button" aria-label="删除规则">×</button>
      </li>
    `)
    .join("");
}

function renderSource() {
  const note = notes[activeNoteIndex];
  sourceTitle.textContent = note.title;
  sourceMeta.textContent = `${note.author} · ${note.likes} 赞 · 模拟采集自关键词「${keywordInput.value || "北京美食"}」`;
  sourceBody.textContent = note.body;
  currentNoteName.textContent = note.title;
}

function renderSummary({ collectedCount = 33 } = {}) {
  const keyword = keywordInput.value || "北京美食";
  summaryCount.textContent = String(collectedCount);
  summaryKeywords.textContent = `${keyword} / 北京烤鸭 / 北京火锅`;
  summaryLatest.textContent = new Date().toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderDrafts(activeTitle = "") {
  draftList.innerHTML = drafts.length
    ? drafts
        .map((draft, index) => `
          <button class="saved-draft ${draft.title === activeTitle || (!activeTitle && index === 0) ? "active" : ""}" data-draft="${index}" type="button">
            <strong>${draft.title}</strong>
            <small>${draft.personaName} · ${draft.noteTitle}</small>
          </button>
        `)
        .join("")
    : `<p class="muted">生成或保存后会在这里形成草稿记录。</p>`;
}

function generateDraft({ save = true } = {}) {
  const note = notes[activeNoteIndex];
  const persona = personas[activePersonaKey];
  const output = persona.rewrite(note);
  draftTitle.value = output.title;
  draftBody.value = output.body;
  tagRow.innerHTML = output.tags.map((tag) => `<span>${tag}</span>`).join("");

  if (save) {
    const nextDraft = {
      title: output.title,
      body: output.body,
      tags: output.tags,
      noteIndex: activeNoteIndex,
      noteTitle: note.title,
      personaKey: activePersonaKey,
      personaName: persona.name,
    };
    drafts = [nextDraft, ...drafts.filter((draft) => draft.title !== output.title)].slice(0, 5);
    renderDrafts(output.title);
  }
}

function selectNote(index) {
  activeNoteIndex = index;
  renderNotes();
  renderSource();
  generateDraft();
}

function selectPersona(key) {
  activePersonaKey = key;
  renderPersonas();
  renderPersonaDetail();
  generateDraft();
}

function restoreDraft(index) {
  const draft = drafts[index];
  if (!draft) return;
  activeNoteIndex = draft.noteIndex;
  activePersonaKey = draft.personaKey;
  draftTitle.value = draft.title;
  draftBody.value = draft.body;
  tagRow.innerHTML = draft.tags.map((tag) => `<span>${tag}</span>`).join("");
  renderPersonas();
  renderNotes();
  renderPersonaDetail();
  renderSource();
  renderDrafts(draft.title);
}

personaList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-persona]");
  if (!button) return;
  selectPersona(button.dataset.persona);
});

noteList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-note]");
  if (!button) return;
  selectNote(Number(button.dataset.note));
});

draftList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-draft]");
  if (!button) return;
  restoreDraft(Number(button.dataset.draft));
});

document.querySelector("#generateButton").addEventListener("click", () => generateDraft());

document.querySelector("#saveButton").addEventListener("click", () => {
  const note = notes[activeNoteIndex];
  const persona = personas[activePersonaKey];
  const savedDraft = {
    title: draftTitle.value,
    body: draftBody.value,
    tags: Array.from(tagRow.querySelectorAll("span")).map((tag) => tag.textContent),
    noteIndex: activeNoteIndex,
    noteTitle: note.title,
    personaKey: activePersonaKey,
    personaName: persona.name,
  };
  drafts = [savedDraft, ...drafts.filter((draft) => draft.title !== savedDraft.title)].slice(0, 5);
  renderDrafts(savedDraft.title);
});

document.querySelector("#editPersonaButton").addEventListener("click", () => {
  personaDescription.focus();
  ruleStatus.textContent = "可以直接编辑当前人设描述";
});

personaDescription.addEventListener("input", () => {
  personas[activePersonaKey].description = personaDescription.value;
  renderPersonas();
});

document.querySelector("#newPersonaButton").addEventListener("click", () => {
  const key = `persona${Object.keys(personas).length + 1}`;
  personas[key] = {
    name: "新人人设",
    description: "可在这里填写目标账号的身份、语气、内容偏好和禁用表达。",
    rules: ["先保留一条默认规则：表达要贴近目标用户的真实语气。"],
    rewrite(note) {
      return {
        title: `${note.title}，换一种账号口吻重新讲`,
        body: `这条素材可以根据新人人设继续改写。\n\n${note.body}\n\n在真实工作台里，用户会先补充人设描述和风格规则，再调用 AI 生成更贴合账号的草稿。`,
        tags: note.tags.concat(["新人设", "内容二创"]),
      };
    },
  };
  selectPersona(key);
  ruleStatus.textContent = "已创建一个空白人设，可继续编辑描述和规则";
});

document.querySelector("#addRuleButton").addEventListener("click", () => {
  const value = newRuleInput.value.trim();
  if (!value) {
    ruleStatus.textContent = "先输入一条想沉淀的风格规则";
    return;
  }
  personas[activePersonaKey].rules = [value, ...personas[activePersonaKey].rules].slice(0, 6);
  newRuleInput.value = "";
  renderPersonaDetail();
  ruleStatus.textContent = "已手动添加一条规则";
});

ruleList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-rule]");
  if (!button) return;
  const index = Number(button.dataset.rule);
  personas[activePersonaKey].rules.splice(index, 1);
  renderPersonaDetail();
  ruleStatus.textContent = "已删除一条规则";
});

document.querySelector("#collectButton").addEventListener("click", () => {
  const button = document.querySelector("#collectButton");
  button.textContent = "采集中";
  button.disabled = true;
  collectStatus.textContent = `正在模拟采集「${keywordInput.value || "北京美食"}」${collectCountInput.value || "10"} 条素材...`;
  setTimeout(() => {
    button.textContent = "模拟采集";
    button.disabled = false;
    const nextCount = Math.max(Number(collectCountInput.value) || notes.length, notes.length);
    collectStatus.textContent = `已采集到一批可用于二创的素材，左侧列表展示其中 ${notes.length} 条示例。`;
    renderSummary({ collectedCount: nextCount });
    selectNote((activeNoteIndex + 1) % notes.length);
  }, 700);
});

document.querySelector("#refineButton").addEventListener("click", () => {
  const persona = personas[activePersonaKey];
  const candidate = activePersonaKey === "xiaobai"
    ? "标题表达保持活泼，但同一类情绪词不要连续重复。"
    : "正文优先补足消费决策信息，再保留个人体验。";
  if (!persona.rules.includes(candidate)) {
    persona.rules = [candidate, ...persona.rules].slice(0, 6);
    renderPersonaDetail();
    ruleStatus.textContent = `已加入「${persona.name}」人设规则`;
    return;
  }
  ruleStatus.textContent = "这条候选规则已经在当前人设里";
});

renderPersonas();
renderNotes();
renderPersonaDetail();
renderSource();
renderSummary();
generateDraft();
