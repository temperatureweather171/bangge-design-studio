const grid = document.querySelector("#project-grid");
const header = document.querySelector(".site-header");
const modal = document.querySelector("#project-modal");
const modalIndex = document.querySelector("#modal-index");
const modalTitle = document.querySelector("#modal-title");
const modalMeta = document.querySelector("#modal-meta");
const modalSummary = document.querySelector("#modal-summary");
const modalGallery = document.querySelector("#modal-gallery");

let projects = [];
let lastFocusedElement = null;

const escapeHtml = (value = "") =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const projectNumber = (index) => String(index + 1).padStart(2, "0");

const excerpt = (text, limit = 118) => {
  if (!text || text.length <= limit) return text || "";
  const clipped = text.slice(0, limit);
  const stop = Math.max(clipped.lastIndexOf("。"), clipped.lastIndexOf("；"));
  return `${clipped.slice(0, stop > 48 ? stop + 1 : limit).replace(/[，、；：]$/, "")}...`;
};

const renderMeta = (project) => {
  const meta = [project.location, project.area].filter(Boolean);
  return meta.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
};

const cardTemplate = (project, index) => {
  const cover = project.images?.[0];
  const imageMarkup = cover
    ? `<img
        src="${escapeHtml(cover.small)}"
        srcset="${escapeHtml(cover.small)} 900w, ${escapeHtml(cover.src)} 1900w"
        sizes="(max-width: 900px) 100vw, ${project.featured ? "58vw" : "34vw"}"
        alt="${escapeHtml(cover.alt)}"
        loading="${index < 2 ? "eager" : "lazy"}"
      />`
    : "";

  return `
    <button class="project-card${project.featured ? " featured" : ""}" type="button" data-project-id="${escapeHtml(project.id)}">
      <span class="project-image">${imageMarkup}</span>
      <span class="project-info">
        <span class="project-number">PROJECT ${projectNumber(index)}</span>
        <span class="project-title">${escapeHtml(project.title)}</span>
        <span class="project-meta">${renderMeta(project)}</span>
        <span class="project-summary">${escapeHtml(excerpt(project.summary))}</span>
      </span>
    </button>
  `;
};

const renderProjects = () => {
  grid.innerHTML = projects.map(cardTemplate).join("");
};

const buildModalMeta = (project) => {
  const rows = [
    ["地点", project.location],
    ["面积", project.area],
    ["图片", `${project.images.length} 张`],
  ].filter(([, value]) => value);

  modalMeta.innerHTML = rows
    .map(([label, value]) => `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`)
    .join("");
};

const buildGallery = (project) => {
  modalGallery.innerHTML = project.images
    .map(
      (image) => `
        <figure>
          <img
            src="${escapeHtml(image.small)}"
            srcset="${escapeHtml(image.small)} 900w, ${escapeHtml(image.src)} 1900w"
            sizes="(max-width: 900px) 100vw, 58vw"
            width="${escapeHtml(image.width)}"
            height="${escapeHtml(image.height)}"
            alt="${escapeHtml(image.alt)}"
            loading="lazy"
          />
        </figure>
      `,
    )
    .join("");
};

const openProject = (projectId) => {
  const project = projects.find((item) => item.id === projectId);
  if (!project) return;

  const index = projects.indexOf(project);
  lastFocusedElement = document.activeElement;
  modalIndex.textContent = `PROJECT ${projectNumber(index)}`;
  modalTitle.textContent = project.title;
  modalSummary.textContent = project.summary;
  buildModalMeta(project);
  buildGallery(project);

  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  modal.querySelector(".modal-close").focus();
};

const closeModal = () => {
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  modalGallery.innerHTML = "";
  if (lastFocusedElement) lastFocusedElement.focus();
};

const loadProjects = async () => {
  try {
    const response = await fetch("./assets/data/projects.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    projects = data.projects || [];
    renderProjects();
  } catch (error) {
    grid.innerHTML =
      '<p class="error-note">作品数据暂时无法载入。请通过本地预览服务器打开网站，而不是直接双击 HTML 文件。</p>';
    console.error(error);
  }
};

grid.addEventListener("click", (event) => {
  const card = event.target.closest("[data-project-id]");
  if (card) openProject(card.dataset.projectId);
});

modal.addEventListener("click", (event) => {
  if (event.target.closest("[data-close-modal]")) closeModal();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && modal.classList.contains("is-open")) closeModal();
});

window.addEventListener(
  "scroll",
  () => {
    header.classList.toggle("is-scrolled", window.scrollY > 12);
  },
  { passive: true },
);

loadProjects();
