import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Download, RefreshCcw, Sparkles, Trash2, Wand2 } from "lucide-react";
import { api, ASSET_BASE } from "./api";
import "./styles.css";

function formatNumber(value) {
  const n = Number(value || 0);
  if (n >= 10000) return `${(n / 10000).toFixed(1)}万`;
  return String(n);
}

function firstImage(note) {
  const image = note?.images?.[0];
  return image ? `${ASSET_BASE}/${image.local_path}` : "";
}

function App() {
  const [health, setHealth] = useState(null);
  const [keyword, setKeyword] = useState("北京美食");
  const [limit, setLimit] = useState(10);
  const [notes, setNotes] = useState([]);
  const [personas, setPersonas] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [selectedNoteId, setSelectedNoteId] = useState(null);
  const [selectedPersonaId, setSelectedPersonaId] = useState(null);
  const [libraryFilter, setLibraryFilter] = useState("");
  const [activeDraft, setActiveDraft] = useState(null);
  const [finalTitle, setFinalTitle] = useState("");
  const [finalBody, setFinalBody] = useState("");
  const [personaForm, setPersonaForm] = useState({ name: "小白", description: "00后女大学生，语言生动活泼，喜欢用真实体验和轻松吐槽表达。" });
  const [editingPersonaId, setEditingPersonaId] = useState(null);
  const [newRule, setNewRule] = useState("");
  const [ruleSuggestions, setRuleSuggestions] = useState([]);
  const [message, setMessage] = useState("");
  const [remixError, setRemixError] = useState("");
  const [localExport, setLocalExport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [collecting, setCollecting] = useState(false);

  const selectedNote = useMemo(() => notes.find((note) => note.id === selectedNoteId), [notes, selectedNoteId]);
  const selectedPersona = useMemo(() => personas.find((persona) => persona.id === selectedPersonaId), [personas, selectedPersonaId]);
  const visibleNotes = useMemo(() => {
    const term = libraryFilter.trim();
    if (!term) return notes;
    return notes.filter((note) => `${note.keyword} ${note.title} ${note.author} ${note.content}`.includes(term));
  }, [notes, libraryFilter]);
  const collectedKeywords = useMemo(() => [...new Set(notes.map((note) => note.keyword).filter(Boolean))], [notes]);
  const latestCollectedAt = useMemo(() => notes.map((note) => note.collected_at).filter(Boolean).sort().at(-1), [notes]);

  async function loadAll() {
    const [healthData, notesData, personasData, draftsData] = await Promise.all([
      api.health(),
      api.notes(),
      api.personas(),
      api.drafts(),
    ]);
    setHealth(healthData);
    setNotes(notesData);
    setPersonas(personasData);
    setDrafts(draftsData);
    if (!selectedNoteId && notesData[0]) setSelectedNoteId(notesData[0].id);
    if (!selectedPersonaId && personasData[0]) setSelectedPersonaId(personasData[0].id);
  }

  useEffect(() => {
    loadAll().catch((error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    if (!selectedPersona) return;
    setEditingPersonaId(selectedPersona.id);
    setPersonaForm({ name: selectedPersona.name, description: selectedPersona.description });
  }, [selectedPersonaId, selectedPersona]);

  async function runBusy(fn) {
    setBusy(true);
    setMessage("");
    setRemixError("");
    try {
      await fn();
    } catch (error) {
      setMessage(error.message);
      setRemixError(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function collect() {
    setCollecting(true);
    try {
      await runBusy(async () => {
        const result = await api.collect({ keyword, limit: Number(limit) });
        setMessage(`采集完成：发现 ${result.stats.found} 条，保存 ${result.stats.saved} 条，失败 ${result.stats.failed} 条`);
        setLibraryFilter(keyword);
        await loadAll();
        if (result.notes?.[0]?.id) {
          setSelectedNoteId(result.notes[0].id);
        }
      });
    } finally {
      setCollecting(false);
    }
  }

  async function savePersona() {
    await runBusy(async () => {
      if (editingPersonaId) {
        await api.updatePersona(editingPersonaId, personaForm);
        setMessage("人设已更新");
      } else {
        const created = await api.createPersona(personaForm);
        setSelectedPersonaId(created.id);
        setMessage("人设已创建");
      }
      await loadAll();
    });
  }

  function startNewPersona() {
    setEditingPersonaId(null);
    setSelectedPersonaId(null);
    setPersonaForm({ name: "", description: "" });
  }

  async function addRule(ruleText = newRule) {
    if (!selectedPersonaId || !ruleText.trim()) return;
    await runBusy(async () => {
      await api.addRule(selectedPersonaId, { rule_text: ruleText.trim() });
      setNewRule("");
      await loadAll();
    });
  }

  async function generateDraft() {
    if (!selectedNoteId || !selectedPersonaId) {
      setRemixError("请先在左侧素材库选择一条帖子，并在人设区选择“小白”。");
      return;
    }
    await runBusy(async () => {
      const draft = await api.generateDraft({ note_id: selectedNoteId, persona_id: selectedPersonaId });
      setActiveDraft(draft);
      setFinalTitle(draft.generated_title);
      setFinalBody(draft.generated_body);
      setRuleSuggestions([]);
      setLocalExport(null);
      await loadAll();
    });
  }

  async function saveDraft() {
    if (!activeDraft) return;
    await runBusy(async () => {
      const draft = await api.saveDraft(activeDraft.id, { final_title: finalTitle, final_body: finalBody });
      setActiveDraft(draft);
      setMessage("终稿已保存，编辑记录已入库");
      await loadAll();
    });
  }

  async function suggestRules() {
    if (!activeDraft) return;
    await runBusy(async () => {
      const result = await api.suggestRules(activeDraft.id);
      setRuleSuggestions(result.rules);
    });
  }

  async function exportDraft() {
    if (!activeDraft) return;
    await runBusy(async () => {
      const result = await api.exportDraft(activeDraft.id);
      await navigator.clipboard.writeText(result.markdown);
      setMessage("Markdown 已复制到剪贴板");
    });
  }

  async function exportDraftLocal() {
    if (!activeDraft) return;
    await runBusy(async () => {
      const result = await api.exportDraftLocal(activeDraft.id);
      setLocalExport(result);
      setMessage(`保存成功：${result.export_dir}（${result.image_count} 张图片）`);
    });
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>小红书 AI 二创工作台</h1>
          <p>OpenCLI 采集素材，按人设生成草稿，再从你的编辑里养出更像你的风格。</p>
        </div>
        <button className="icon-button" onClick={() => loadAll()} title="刷新">
          <RefreshCcw size={18} />
        </button>
      </header>

      {message && <div className="notice">{message}</div>}
      {health?.opencli && !health.opencli.ok && <div className="error">{health.opencli.message}</div>}
      {!health && (
        <div className="error">
          没有连上后端 API。请确认后端已启动：cd xiaohongshu-remix-studio/backend && source .venv/bin/activate && python run.py
        </div>
      )}

      <section className="status-row">
        <div className="status-card">
          <span>已采集帖子</span>
          <strong>{notes.length}</strong>
        </div>
        <div className="status-card">
          <span>关键词</span>
          <strong>{collectedKeywords.length ? collectedKeywords.join(" / ") : "暂无"}</strong>
        </div>
        <div className="status-card">
          <span>最近采集</span>
          <strong>{latestCollectedAt || "暂无"}</strong>
        </div>
        <div className={health?.opencli?.ok ? "status-card ok" : "status-card warn"}>
          <span>OpenCLI</span>
          <strong>{health?.opencli?.ok ? "可用" : "未确认"}</strong>
        </div>
      </section>

      <main className="layout">
        <section className="panel collect-panel">
          <h2>采集</h2>
          <div className="form-row">
            <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="关键词，如 北京美食" />
            <input type="number" min="1" max="50" value={limit} onChange={(event) => setLimit(event.target.value)} />
            <button onClick={collect} disabled={busy || collecting}>{collecting ? "采集中..." : "采集素材"}</button>
          </div>
          {collecting && (
            <div className="collect-hint">
              OpenCLI 正在逐条获取帖子正文和图片，可能需要几十秒。完成后素材库会自动刷新；如果你切走了页面，稍后手动刷新也可以。
            </div>
          )}
        </section>

        <section className="panel persona-panel">
          <div className="persona-heading">
            <h2>人设</h2>
            <p>先选择写作口吻，再到下方选择素材生成草稿。</p>
          </div>
          <div className="persona-row">
            <div className="form-grid persona-form">
              <input value={personaForm.name} onChange={(event) => setPersonaForm({ ...personaForm, name: event.target.value })} placeholder="人设名称" />
              <textarea value={personaForm.description} onChange={(event) => setPersonaForm({ ...personaForm, description: event.target.value })} placeholder="人设描述" />
              <div className="persona-form-actions">
                <button onClick={savePersona} disabled={busy || !personaForm.name.trim() || !personaForm.description.trim()}>
                  {editingPersonaId ? "保存人设" : "新建人设"}
                </button>
                <button className="secondary-button" onClick={startNewPersona} disabled={busy}>新建空白</button>
              </div>
            </div>
            <div className="persona-list">
              {personas.map((persona) => (
                <button
                  key={persona.id}
                  className={persona.id === selectedPersonaId ? "persona active" : "persona"}
                  onClick={() => setSelectedPersonaId(persona.id)}
                >
                  <strong>{persona.name}</strong>
                  <span>{persona.description}</span>
                </button>
              ))}
            </div>
            {selectedPersona && (
              <div className="rules">
                <h3>{selectedPersona.name} 的风格规则</h3>
                <div className="rule-input">
                  <input value={newRule} onChange={(event) => setNewRule(event.target.value)} placeholder="手动添加一条规则" />
                  <button onClick={() => addRule()}>添加</button>
                </div>
                {(selectedPersona.rules || []).map((rule) => (
                  <div className="rule" key={rule.id}>
                    <span>{rule.rule_text}</span>
                    <button onClick={() => runBusy(async () => { await api.deleteRule(rule.id); await loadAll(); })} title="删除规则">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="panel library-panel">
          <h2>已采集素材（{visibleNotes.length}/{notes.length}）</h2>
          <p className="panel-hint">点击任意卡片，右侧会显示完整正文和图片。</p>
          <input
            className="library-filter"
            value={libraryFilter}
            onChange={(event) => setLibraryFilter(event.target.value)}
            placeholder="筛选关键词，如 北京烤鸭"
          />
          <div className="note-list">
            {visibleNotes.map((note) => (
              <button
                key={note.id}
                className={note.id === selectedNoteId ? "note-card active" : "note-card"}
                onClick={() => setSelectedNoteId(note.id)}
              >
                {firstImage(note) ? <img src={firstImage(note)} alt="" /> : <div className="image-placeholder">无图</div>}
                <div>
                  <strong>{note.title || "无标题"}</strong>
                  <span>#{note.keyword} · @{note.author || "未知"} · {formatNumber(note.likes)} 赞 · {note.status}</span>
                  <p>{note.content || note.error_message || "暂无正文"}</p>
                </div>
              </button>
            ))}
            {!visibleNotes.length && (
              <div className="empty-state">
                暂无匹配素材。可以清空筛选，或在上方输入关键词并点击“采集素材”。
              </div>
            )}
          </div>
        </section>

        <section className="compare-workbench">
          <div className="workbench-header">
            <div className="workbench-context">
              <span>素材：{selectedNote?.title || "未选择"}</span>
              <span>人设：{selectedPersona?.name || "未选择"}</span>
            </div>
          </div>

          <section className="panel source-panel">
            <h2>原帖</h2>
            {selectedNote ? (
              <>
                <h3>{selectedNote.title}</h3>
                <p className="muted">@{selectedNote.author} · {formatNumber(selectedNote.likes)} 赞</p>
                <div className="image-strip">
                  {(selectedNote.images || []).map((image) => (
                    <img key={image.id} src={`${ASSET_BASE}/${image.local_path}`} alt="" />
                  ))}
                </div>
                <p className="source-content">{selectedNote.content || selectedNote.error_message}</p>
                <a href={selectedNote.url} target="_blank" rel="noreferrer">打开原链接</a>
              </>
            ) : <p className="muted">暂无素材</p>}
          </section>

          <section className="panel remix-panel">
            <div className="panel-header">
              <h2>二创草稿</h2>
              <button onClick={generateDraft} disabled={busy}>
                <Wand2 size={16} /> {busy ? "生成中..." : "生成"}
              </button>
            </div>
            <div className="selection-summary">
              <div>
                <span>当前素材</span>
                <strong>{selectedNote?.title || "未选择"}</strong>
              </div>
              <div>
                <span>当前人设</span>
                <strong>{selectedPersona?.name || "未选择"}</strong>
              </div>
            </div>
            {remixError && <div className="inline-error">{remixError}</div>}
            {activeDraft ? (
              <>
                <label>标题</label>
                <input value={finalTitle} onChange={(event) => setFinalTitle(event.target.value)} />
                <label>正文</label>
                <textarea className="draft-body" value={finalBody} onChange={(event) => setFinalBody(event.target.value)} />
                <div className="draft-meta">
                  <span>建议标签：{activeDraft.suggested_tags}</span>
                  <span>图片建议：{activeDraft.image_advice}</span>
                </div>
                {(selectedNote?.images || []).length > 0 && (
                  <div className="remix-images">
                    <h3>配图</h3>
                    <div className="remix-image-grid">
                      {selectedNote.images.map((image) => (
                        <img key={image.id} src={`${ASSET_BASE}/${image.local_path}`} alt="" />
                      ))}
                    </div>
                  </div>
                )}
                <div className="actions">
                  <button onClick={saveDraft} disabled={busy}>保存终稿</button>
                  <button onClick={suggestRules} disabled={busy}><Sparkles size={16} /> 提炼规则</button>
                  <button onClick={exportDraft} disabled={busy}><Download size={16} /> 复制 Markdown</button>
                  <button onClick={exportDraftLocal} disabled={busy}><Download size={16} /> 保存到本地</button>
                </div>
                {localExport && (
                  <div className="export-success">
                    <strong>保存成功</strong>
                    <span>目录：{localExport.export_dir}</span>
                    <span>文件：{localExport.markdown_path}</span>
                    <span>图片：{localExport.image_count} 张</span>
                  </div>
                )}
                {ruleSuggestions.length > 0 && (
                  <div className="suggestions">
                    <h3>候选规则</h3>
                    {ruleSuggestions.map((rule) => (
                      <button key={rule} onClick={() => addRule(rule)}>{rule}</button>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="muted">选择素材和人设后生成草稿。</p>
            )}
          </section>
        </section>

        <section className="panel drafts-panel">
          <h2>草稿库</h2>
          <div className="draft-list">
            {drafts.map((draft) => (
              <button
                key={draft.id}
                onClick={() => {
                  setActiveDraft(draft);
                  setSelectedNoteId(draft.note_id);
                  setSelectedPersonaId(draft.persona_id);
                  setFinalTitle(draft.final_title || draft.generated_title);
                  setFinalBody(draft.final_body || draft.generated_body);
                }}
              >
                <strong>{draft.final_title || draft.generated_title}</strong>
                <span>{draft.status} · {draft.updated_at}</span>
              </button>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
