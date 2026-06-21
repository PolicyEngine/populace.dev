(() => {
  const graph = document.querySelector(".axiom-graph-shell");
  if (!graph) return;

  const canvasWrap = graph.querySelector(".concept-network");
  const canvas = graph.querySelector("#spec-graph-canvas");
  const lines = graph.querySelector("#spec-graph-lines");
  const minimap = graph.querySelector("#graph-minimap");
  const filters = graph.querySelector("#graph-filters");
  const stats = graph.querySelector("#graph-stats");
  const shapeKey = graph.querySelector("#graph-shape-key");
  const source = graph.querySelector("#graph-source");
  const dependencyTable = graph.querySelector("#graph-dependencies");
  const viewButtons = Array.from(graph.querySelectorAll(".graph-toolbar-btn[data-view]"));
  const fitButton = graph.querySelector(".graph-toolbar-btn[data-action='fit']");
  const inspector = {
    kind: graph.querySelector("#graph-inspector-kind"),
    title: graph.querySelector("#graph-inspector-title"),
    description: graph.querySelector("#graph-inspector-description"),
    inputs: graph.querySelector("#graph-inspector-inputs"),
    outputs: graph.querySelector("#graph-inspector-outputs"),
    attributes: graph.querySelector("#graph-inspector-attributes"),
  };

  const state = {
    spec: null,
    nodeById: new Map(),
    selectedId: null,
    activeGroup: "all",
    activeView: "full",
  };

  const escapeHtml = (value = "") =>
    String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");

  function shapeClass(shape) {
    if (shape === "input") return "node-input";
    if (shape === "output") return "node-output";
    if (shape === "attribute") return "node-attribute";
    return "node-rule";
  }

  function visibleForView(node) {
    return state.activeView === "full" || node.shape !== "attribute";
  }

  function visibleForFilter(node) {
    return state.activeGroup === "all" || node.group === state.activeGroup;
  }

  function groupLabel(groupId) {
    return state.spec.groups.find((group) => group.id === groupId)?.label || groupId;
  }

  function nodeLabel(node) {
    const preview = node.attributes?.slice(0, 2).join(", ") || node.summary;
    return `
      <span class="node-kind mono">${escapeHtml(node.kind)}</span>
      <strong>${escapeHtml(node.title)}</strong>
      <small>${escapeHtml(preview)}</small>
    `;
  }

  function renderStats() {
    const groupCount = new Set(state.spec.nodes.map((node) => node.group)).size;
    const computed = [
      { label: "nodes", value: state.spec.nodes.length },
      { label: "edges", value: state.spec.edges.length },
      { label: "groups", value: groupCount },
      ...state.spec.stats,
    ];
    stats.innerHTML = computed
      .map(
        (item) => `
          <article>
            <strong>${escapeHtml(item.value)}</strong>
            <span>${escapeHtml(item.label)}</span>
          </article>
        `,
      )
      .join("");
  }

  function renderFilters() {
    const buttons = [
      { id: "all", label: "All" },
      ...state.spec.groups.map((group) => ({ id: group.id, label: group.label })),
    ];
    filters.innerHTML = buttons
      .map(
        (group) => `
          <button type="button" class="graph-filter-btn ${group.id === state.activeGroup ? "is-active" : ""}" data-group="${escapeHtml(group.id)}">
            ${escapeHtml(group.label)}
          </button>
        `,
      )
      .join("");
    filters.querySelectorAll(".graph-filter-btn").forEach((button) => {
      button.addEventListener("click", () => {
        state.activeGroup = button.dataset.group || "all";
        state.selectedId = null;
        renderGraphState();
      });
    });
  }

  function renderShapeKey() {
    shapeKey.innerHTML = state.spec.shapeLegend
      .map(
        (item) => `
          <span>
            <i class="shape-${escapeHtml(item.shape)}"></i>
            ${escapeHtml(item.label)}
          </span>
        `,
      )
      .join("");
  }

  function shortSha(value = "") {
    return String(value).slice(0, 7);
  }

  function renderSourceProvenance() {
    const repositories = state.spec.source?.repositories || {};
    const generatedAt = state.spec.generated_at
      ? new Date(state.spec.generated_at).toLocaleString(undefined, {
          month: "short",
          day: "numeric",
          hour: "numeric",
          minute: "2-digit",
        })
      : "";
    const repoLines = Object.values(repositories)
      .map((repo) => `${repo.label || repo.repository}@${shortSha(repo.commit || repo.ref)}${repo.dirty === "true" ? " dirty" : ""}`)
      .join(" · ");
    source.textContent = [repoLines, generatedAt ? `generated ${generatedAt}` : ""].filter(Boolean).join(" · ");
  }

  function edgePath(edge) {
    const source = state.nodeById.get(edge.from);
    const target = state.nodeById.get(edge.to);
    if (!source || !target) return "";
    const forward = target.x >= source.x;
    const sourceHalf = source.shape === "attribute" ? 52 : 62;
    const targetHalf = target.shape === "attribute" ? 52 : 62;
    const sx = source.x + (forward ? sourceHalf : -sourceHalf);
    const tx = target.x + (forward ? -targetHalf : targetHalf);
    const sy = source.y;
    const ty = target.y;
    const dx = Math.max(70, Math.abs(tx - sx) * 0.42);
    const c1 = forward ? sx + dx : sx - dx;
    const c2 = forward ? tx - dx : tx + dx;
    return `M ${sx} ${sy} C ${c1} ${sy}, ${c2} ${ty}, ${tx} ${ty}`;
  }

  function renderCanvas() {
    const { width, height } = state.spec.canvas;
    canvas.style.setProperty("--graph-width", `${width}px`);
    canvas.style.setProperty("--graph-height", `${height}px`);
    lines.setAttribute("viewBox", `0 0 ${width} ${height}`);
    lines.setAttribute("width", width);
    lines.setAttribute("height", height);
    lines.innerHTML = `
      <defs>
        <marker id="graph-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" />
        </marker>
      </defs>
      ${state.spec.edges
        .map(
          (edge) => `
            <path data-from="${escapeHtml(edge.from)}" data-to="${escapeHtml(edge.to)}" d="${edgePath(edge)}" />
          `,
        )
        .join("")}
    `;

    canvas.querySelectorAll(".concept-node").forEach((node) => node.remove());
    state.spec.nodes.forEach((node) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `concept-node ${shapeClass(node.shape)}`;
      button.dataset.node = node.id;
      button.dataset.group = node.group;
      button.style.setProperty("--x", `${node.x}px`);
      button.style.setProperty("--y", `${node.y}px`);
      button.innerHTML = nodeLabel(node);
      button.addEventListener("click", () => {
        state.selectedId = node.id;
        state.activeGroup = "all";
        renderGraphState();
      });
      canvas.appendChild(button);
    });

    minimap.innerHTML = state.spec.nodes
      .map(
        (node) => `
          <span data-node="${escapeHtml(node.id)}" style="--x:${(node.x / width) * 100}%; --y:${(node.y / height) * 100}%;"></span>
        `,
      )
      .join("");
  }

  function directEdges(nodeId) {
    return state.spec.edges.filter((edge) => edge.from === nodeId || edge.to === nodeId);
  }

  function relatedNodeIds(nodeId) {
    const related = new Set([nodeId]);
    directEdges(nodeId).forEach((edge) => {
      related.add(edge.from);
      related.add(edge.to);
    });
    return related;
  }

  function setInspector(node) {
    if (!node) {
      inspector.kind.textContent = "filtered view";
      inspector.title.textContent = state.activeGroup === "all" ? "Full schema" : groupLabel(state.activeGroup);
      inspector.description.textContent =
        state.activeGroup === "all"
          ? "All Ledger and Populace concepts are visible."
          : `Showing the ${groupLabel(state.activeGroup)} concept group.`;
      inspector.inputs.textContent = "select a node";
      inspector.outputs.textContent = "select a node";
      inspector.attributes.textContent = "select a node";
      return;
    }

    const incoming = state.spec.edges.filter((edge) => edge.to === node.id);
    const outgoing = state.spec.edges.filter((edge) => edge.from === node.id);
    inspector.kind.textContent = `${node.kind} - ${groupLabel(node.group)}`;
    inspector.title.textContent = node.title;
    inspector.description.textContent = node.summary;
    inspector.inputs.textContent = incoming.map((edge) => state.nodeById.get(edge.from)?.title || edge.from).join(", ") || "none";
    inspector.outputs.textContent = outgoing.map((edge) => state.nodeById.get(edge.to)?.title || edge.to).join(", ") || "none";
    inspector.attributes.innerHTML = `<ul>${(node.attributes || []).map((attribute) => `<li>${escapeHtml(attribute)}</li>`).join("")}</ul>`;
  }

  function setDependencyTable(node) {
    const rows = (node ? directEdges(node.id) : state.spec.edges.slice(0, 8)).map((edge) => ({
      from: state.nodeById.get(edge.from)?.title || edge.from,
      to: state.nodeById.get(edge.to)?.title || edge.to,
      contract: edge.contract || edge.label || "",
    }));
    dependencyTable.innerHTML = rows
      .map(
        (row) => `
          <div class="dep-row" role="row">
            <span>${escapeHtml(row.from)}</span>
            <span>${escapeHtml(row.to)}</span>
            <span>${escapeHtml(row.contract)}</span>
          </div>
        `,
      )
      .join("");
  }

  function renderGraphState() {
    if (!state.spec) return;
    const selected = state.selectedId ? state.nodeById.get(state.selectedId) : null;
    const related = selected ? relatedNodeIds(selected.id) : new Set();

    graph.querySelectorAll(".graph-filter-btn").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.group === state.activeGroup);
    });

    graph.querySelectorAll(".concept-node").forEach((element) => {
      const node = state.nodeById.get(element.dataset.node);
      const visible = node && visibleForView(node) && visibleForFilter(node);
      const onPath = selected && related.has(node.id);
      element.classList.toggle("is-hidden", !visible);
      element.classList.toggle("is-active", selected?.id === node?.id);
      element.classList.toggle("is-path", !!onPath && selected?.id !== node?.id);
      element.classList.toggle("is-muted", !!selected && visible && !onPath);
    });

    lines.querySelectorAll("path[data-from]").forEach((path) => {
      const from = state.nodeById.get(path.dataset.from);
      const to = state.nodeById.get(path.dataset.to);
      const visible =
        from &&
        to &&
        visibleForView(from) &&
        visibleForView(to) &&
        visibleForFilter(from) &&
        visibleForFilter(to);
      const onPath = selected && (path.dataset.from === selected.id || path.dataset.to === selected.id);
      path.classList.toggle("is-hidden", !visible);
      path.classList.toggle("is-path", !!onPath);
      path.classList.toggle("is-muted", !!selected && visible && !onPath);
    });

    minimap.querySelectorAll("span[data-node]").forEach((dot) => {
      const node = state.nodeById.get(dot.dataset.node);
      const visible = node && visibleForView(node) && visibleForFilter(node);
      dot.classList.toggle("is-hidden", !visible);
      dot.classList.toggle("is-active", selected?.id === node?.id);
    });

    setInspector(selected);
    setDependencyTable(selected);
  }

  function setView(view) {
    if (!state.spec) return;
    state.activeView = view;
    viewButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.view === view);
    });
    canvasWrap?.classList.toggle("is-concepts", view === "concepts");
    renderGraphState();
  }

  async function loadSpecGraph() {
    canvas.insertAdjacentHTML("beforeend", '<div class="graph-loading mono">Loading spec graph...</div>');
    const response = await fetch("./data/spec-graph.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Spec graph request failed: ${response.status}`);
    return response.json();
  }

  loadSpecGraph()
    .then((spec) => {
      state.spec = spec;
      state.nodeById = new Map(spec.nodes.map((node) => [node.id, node]));
      state.selectedId = spec.nodes.some((node) => node.id === state.selectedId)
        ? state.selectedId
        : spec.defaultNode || spec.nodes[0]?.id;
      graph.querySelector("#graph-title").textContent = spec.title;
      graph.querySelector("#graph-description").textContent = spec.description;
      canvas.querySelector(".graph-loading")?.remove();
      renderStats();
      renderSourceProvenance();
      renderFilters();
      renderShapeKey();
      renderCanvas();
      setView("full");
    })
    .catch((error) => {
      canvas.innerHTML = `<div class="graph-error">${escapeHtml(error.message)}</div>`;
    });

  viewButtons.forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view || "full"));
  });

  fitButton?.addEventListener("click", () => {
    if (!state.spec) return;
    state.selectedId = state.spec.defaultNode || state.spec.nodes[0]?.id;
    state.activeGroup = "all";
    setView("full");
    canvasWrap?.scrollTo({ left: 0, top: 0, behavior: "smooth" });
  });
})();
