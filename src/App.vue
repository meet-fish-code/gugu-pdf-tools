
<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { open } from "@tauri-apps/plugin-dialog";
import { invoke } from "@tauri-apps/api/core";
import { Icon } from "@iconify/vue";
import { getVersion } from "@tauri-apps/api/app";
import { openUrl } from "@tauri-apps/plugin-opener";

// #region 类型定义

/** 工具基本信息 */
type Tool = {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
};

/** 单个文件的处理结果 */
type ResultItem = {
  success: boolean;
  input: string;
  output?: string;
  message: string;
};

/** 批量文件处理结果 */
type ProcessResponse = {
  success: boolean;
  total: number;
  successful: number;
  failed: number;
  results: ResultItem[];
};

/** PDF 密码保护模式 */
type PasswordMode = "view" | "edit" | "both";

/** 系统字体信息 */
type SystemFont = {
  name: string;
  path: string;
  index: number;
};

/** PDF 去水印参数 */
interface RemoveWatermarkParams {
  input_path: string;
  output_path: string;
  page_ranges: string;
  password: string;
  remove_marked_watermarks: boolean;
  remove_watermark_annotations: boolean;
  remove_stamp_annotations: boolean;
  remove_all_annotations: boolean;
}

// #endregion

// #region 工具配置

const tools: Tool[] = [
  {
    id: "merge",
    name: "PDF 合并",
    description: "将多个 PDF 文件合并为一个文件",
    icon: "tabler:layers-intersect",
    category: "页面处理",
  },
  {
    id: "split",
    name: "PDF 拆分",
    description: "按页面拆分 PDF 文档",
    icon: "tabler:scissors",
    category: "页面处理",
  },
  {
    id: "remove_watermark",
    name: "PDF 去水印",
    description: "移除 PDF 文件中的水印",
    icon: "tabler:eraser",
    category: "页面处理",
  },
  {
    id: "watermark",
    name: "PDF 加水印",
    description: "在 PDF 文件中添加水印",
    icon: "tabler:rubber-stamp",
    category: "页面处理",
  },
  {
    id: "compress",
    name: "PDF 压缩",
    description: "减小 PDF 文件体积（部分 PDF 处理后可能变大）",
    icon: "tabler:arrow-autofit-down",
    category: "文件处理",
  },
  {
    id: "word_to_pdf",
    name: "Word 转为 PDF",
    description: "将 Word 文件转换为 PDF 格式",
    icon: "fluent:document-word-16-regular",
    category: "文件处理",
  },
  {
    id: "image_to_pdf",
    name: "图片 转为 PDF",
    description: "将图片文件转换为 PDF 格式",
    icon: "material-symbols:imagesmode-outline",
    category: "文件处理",
  },
  {
    id: "pdf_to_image",
    name: "PDF 转为 图片",
    description: "将 PDF 文件转换为图片格式",
    icon: "ri:file-pdf-2-line",
    category: "文件处理",
  },
  {
    id: "permission",
    name: "PDF 解密",
    description: "处理 PDF 的编辑、复制等权限限制（仅限权限密码）",
    icon: "tabler:circle-key",
    category: "安全与权限",
  },
  {
    id: "encryption",
    name: "PDF 添加密码",
    description: "为 PDF 文件添加密码保护",
    icon: "tabler:lock-password",
    category: "安全与权限",
  },
];

const categories = ["全部工具", "页面处理", "文件处理", "安全与权限"];

// #endregion

// #region 页面基础状态

const activeCategory = ref("全部工具");
const searchText = ref("");

const selectedTool = ref<Tool | null>(null);
const selectedFiles = ref<string[]>([]);
const outputFolder = ref("");

const isProcessing = ref(false);
const statusMessage = ref("");
const processResponse = ref<ProcessResponse | null>(null);

const showDonation = ref(false);
const showAbout = ref(false);
const showFeedback = ref(false);

const appVersion = ref("读取中...");

// 字体预览文本
const fontPreviewText = ref("0123AaBbCc 菜鸟gugu");

// #endregion

// #region 软件更新

const autoCheckUpdate = ref(true);
const checkingUpdate = ref(false);
const showUpdateDialog = ref(false);

const updateStatus = ref<"available" | "latest" | "downloading">("latest");
const latestVersion = ref("");
const updateNotes = ref("");
const downloadProgress = ref(0);

/** 更新弹窗标题 */
const updateTitle = computed(() => {
  switch (updateStatus.value) {
    case "available":
      return "发现新版本";
    case "downloading":
      return "正在更新";
    default:
      return "已经是最新版本";
  }
});

/** 更新弹窗提示 */
const updateMessage = computed(() => {
  switch (updateStatus.value) {
    case "available":
      return "发现新版本，建议更新以获得更好的使用体验。";
    case "downloading":
      return "正在下载更新文件，请稍候...";
    default:
      return "当前已经是最新版本，无需更新。";
  }
});

/**
 * 检查软件更新
 *
 * 当前保留模拟逻辑，后续接入 Tauri Updater。
 */
async function checkUpdate() {
  checkingUpdate.value = true;

  try {
    console.log("后续接入 Tauri 更新检查逻辑");

    await new Promise((resolve) => setTimeout(resolve, 800));

    updateStatus.value = "available";
    latestVersion.value = "0.2.0";
    updateNotes.value = `1. 优化 PDF 压缩功能
2. 修复部分 PDF 转换异常
3. 优化软件运行稳定性
4. 改进用户界面体验`;

    showUpdateDialog.value = true;
  } finally {
    checkingUpdate.value = false;
  }
}

/**
 * 下载并安装更新
 *
 * 当前仅保留更新状态，尚未接入实际下载逻辑。
 */
async function startUpdate() {
  try {
    updateStatus.value = "downloading";
    downloadProgress.value = 0;

    console.log("接入 Tauri Updater 下载和安装逻辑");
  } catch (error) {
    console.error("更新失败：", error);
    updateStatus.value = "latest";
  }
}

// #endregion

// #region PDF 密码保护配置

const passwordMode = ref<PasswordMode>("view");
const userPassword = ref("");
const ownerPassword = ref("");

const allowPrint = ref(true);
const allowCopy = ref(false);
const allowModify = ref(false);

// #endregion

// #region PDF 合并与拆分配置

// PDF 合并后的文件名称
const mergePdfName = ref("合并文件");

// PDF 拆分后的文件名前缀
const splitPdfName = ref("拆分文件");

// PDF 拆分模式
const splitMode = ref<"each" | "range">("each");

// PDF 拆分页码范围
const splitPageRanges = ref("1-3,4-8,9-12");

// #endregion

// #region 图片与 PDF 转换配置

// 图片转 PDF：是否合并为一个 PDF
const mergeImages = ref(true);

// 图片转 PDF：输出文件名称
const imagePdfName = ref("图片合并");

// PDF 转图片：图片格式
const pdfImageFormat = ref<"png" | "jpg">("png");

// PDF 转图片：DPI
const pdfImageDpi = ref(200);

// PDF 转图片：指定页码，留空表示全部页面
const pdfImagePages = ref("");

// #endregion

// #region PDF 加水印配置

// 水印类型
const watermarkType = ref<"text" | "image">("text");

// 文字水印
const watermarkText = ref("内部资料");
const watermarkFontSize = ref(48);
const watermarkFontPath = ref("");
const watermarkColor = ref("#999999");

// 图片水印
const watermarkImagePath = ref("");
const watermarkImageWidth = ref(150);

// 水印公共参数
const watermarkOpacity = ref(0.2);
const watermarkRotation = ref(45);
const watermarkPosition = ref<"center" | "tile">("center");
const watermarkLayer = ref<"foreground" | "background">("foreground");

// 水印应用页面范围
const watermarkPageRanges = ref("all");

// #endregion

// #region PDF 去水印配置

// 去水印应用页面范围
const removeWatermarkPageRanges = ref("all");

// PDF 打开密码
const removeWatermarkPassword = ref("");

// 是否移除咕咕 PDF 专属水印标记
const removeMarkedWatermarks = ref(true);

// 是否移除 Watermark 类型注释
const removeWatermarkAnnotations = ref(true);

// 是否移除 Stamp 类型注释
const removeStampAnnotations = ref(false);

// 是否移除全部 PDF 注释
const removeAllAnnotations = ref(false);

// #endregion

// #region 系统字体

const systemFonts = ref<SystemFont[]>([]);
const selectedFontKey = ref("");
const isLoadingFonts = ref(false);

/** 当前选中的字体 */
const selectedFont = computed(() => {
  return systemFonts.value.find(
    (font) => `${font.path}::${font.index}` === selectedFontKey.value
  );
});

/** 加载系统字体列表 */
async function loadSystemFonts() {
  isLoadingFonts.value = true;

  try {
    const fonts = await invoke<SystemFont[]>("list_system_fonts");

    systemFonts.value = fonts;

    if (fonts.length > 0) {
      selectedFontKey.value = `${fonts[0].path}::${fonts[0].index}`;
    }

    console.log("系统字体数量：", fonts.length);
  } catch (error) {
    console.error("系统字体加载失败：", error);
    statusMessage.value = `系统字体加载失败：${String(error)}`;
  } finally {
    isLoadingFonts.value = false;
  }
}

// #endregion

// #region 关于页面配置

const githubUrl = "https://github.com/meet-fish-code/gugu-pdf-tools";
const giteeUrl = "https://gitee.com/ShiboLee/gugu-pdf-tools";

// 按实际参与人员修改
const teamMembers = [
  { role: "开发", name: "菜鸟gugu" },
  { role: "设计", name: "菜鸟gugu" },
  { role: "测试", name: "菜鸟gugu" },
];

// 第三方开源项目致谢
const openSourceProjects = [
  {
    name: "Tauri",
    description: "桌面应用框架",
    url: "https://github.com/tauri-apps/tauri",
  },
  {
    name: "Vue.js",
    description: "前端界面框架",
    url: "https://github.com/vuejs/core",
  },
  {
    name: "Iconify",
    description: "图标生态与组件支持",
    url: "https://github.com/iconify/iconify",
  },
  {
    name: "word2pdf",
    description: "DOCX 文档转 PDF",
    url: "https://github.com/surenjanath/Word2PDF",
  },
  {
    name: "pikepdf",
    description: "PDF 压缩与密码清理",
    url: "https://github.com/pikepdf/pikepdf",
  },
  {
    name: "pypdf",
    description: "PDF 密码保护与文档处理",
    url: "https://github.com/py-pdf/pypdf",
  },
];

// #endregion

// #region 反馈页面配置
const feedbackUrls = {
  gitee: "https://gitee.com/ShiboLee/gugu-pdf-tools/issues",
  github: "https://github.com/meet-fish-code/gugu-pdf-tools/issues",
};

/** 打开需求与建议页面 */
async function openFeedback(platform: "gitee" | "github") {
  try {
    await openUrl(feedbackUrls[platform]);
    showFeedback.value = false;
  } catch (error) {
    console.error("打开反馈页面失败：", error);
  }
}

// #endregion

// #region 工具类型判断

// 安全与权限
const isEncryptionTool = computed(
  () => selectedTool.value?.id === "encryption"
);

const isPermissionTool = computed(
  () => selectedTool.value?.id === "permission"
);

// 文件转换
const isWordToPdfTool = computed(
  () => selectedTool.value?.id === "word_to_pdf"
);

const isImageToPdfTool = computed(
  () => selectedTool.value?.id === "image_to_pdf"
);

const isPdfToImageTool = computed(
  () => selectedTool.value?.id === "pdf_to_image"
);

// 文件处理
const isCompressTool = computed(
  () => selectedTool.value?.id === "compress"
);

// 页面处理
const isPdfMergeTool = computed(
  () => selectedTool.value?.id === "merge"
);

const isPdfSplitTool = computed(
  () => selectedTool.value?.id === "split"
);

// PDF 水印
const isWatermarkTool = computed(
  () => selectedTool.value?.id === "watermark"
);

const isRemoveWatermarkTool = computed(
  () => selectedTool.value?.id === "remove_watermark"
);

// 是否属于 PDF 安全处理工具
const isSecurityTool = computed(
  () => isEncryptionTool.value || isPermissionTool.value
);

// #endregion

// #region 页面计算属性

/** 根据分类和搜索关键字筛选工具 */
const filteredTools = computed(() => {
  const keyword = searchText.value.trim().toLowerCase();

  return tools.filter((tool) => {
    const matchesCategory =
      activeCategory.value === "全部工具" ||
      tool.category === activeCategory.value;

    const matchesSearch =
      !keyword ||
      tool.name.toLowerCase().includes(keyword) ||
      tool.description.toLowerCase().includes(keyword);

    return matchesCategory && matchesSearch;
  });
});

/** 判断当前工具是否满足基本处理条件 */
const canProcess = computed(() => {
  if (!selectedTool.value || isProcessing.value) {
    return false;
  }

  // PDF 合并至少需要两个文件
  if (isPdfMergeTool.value) {
    return selectedFiles.value.length >= 2 && !!outputFolder.value;
  }

  // PDF 拆分只允许一个文件
  if (isPdfSplitTool.value) {
    return selectedFiles.value.length === 1 && !!outputFolder.value;
  }

  // 其他文件处理工具需要至少一个文件和输出目录
  return selectedFiles.value.length > 0 && !!outputFolder.value;
});

// #endregion

// #region 通用方法

/** 获取文件名称 */
function fileName(path: string) {
  return path.split(/[\\/]/).pop() || path;
}

/** 清除上一次处理结果 */
function clearResult() {
  statusMessage.value = "";
  processResponse.value = null;
}

/** 打开外部网页 */
async function openExternalLink(url: string) {
  if (!url) return;

  try {
    await openUrl(url);
  } catch (error) {
    console.error("打开外部网页失败：", error);
  }
}

// #endregion

// #region 工具切换

/**
 * 打开工具并重置该工具的输入状态
 *
 * 不同工具之间不共用上一次选择的文件和参数。
 */
function openTool(tool: Tool) {
  selectedTool.value = tool;

  selectedFiles.value = [];
  outputFolder.value = "";

  clearResult();

  // PDF 密码保护
  passwordMode.value = "view";
  userPassword.value = "";
  ownerPassword.value = "";

  allowPrint.value = true;
  allowCopy.value = false;
  allowModify.value = false;

  // 图片转 PDF
  mergeImages.value = true;
  imagePdfName.value = "图片合并";

  // PDF 转图片
  pdfImageFormat.value = "png";
  pdfImageDpi.value = 200;
  pdfImagePages.value = "";

  // PDF 合并
  mergePdfName.value = "合并文件";

  // PDF 拆分
  splitPdfName.value = "拆分文件";
  splitMode.value = "each";
  splitPageRanges.value = "1-3,4-8,9-12";

  // PDF 加水印
  watermarkType.value = "text";
  watermarkText.value = "内部资料";
  watermarkFontSize.value = 48;
  watermarkFontPath.value = "";
  watermarkColor.value = "#999999";

  watermarkImagePath.value = "";
  watermarkImageWidth.value = 150;

  watermarkOpacity.value = 0.2;
  watermarkRotation.value = 45;
  watermarkPosition.value = "center";
  watermarkLayer.value = "foreground";
  watermarkPageRanges.value = "all";

  // PDF 去水印
  removeWatermarkPageRanges.value = "all";
  removeWatermarkPassword.value = "";

  removeMarkedWatermarks.value = true;
  removeWatermarkAnnotations.value = true;
  removeStampAnnotations.value = false;
  removeAllAnnotations.value = false;
}

/** 关闭工具面板 */
function closeTool() {
  if (isProcessing.value) return;

  selectedTool.value = null;
}

// #endregion

// #region 文件选择与目录操作

/** 根据当前工具选择对应的文件类型 */
async function chooseFiles() {
  try {
    const isWord = isWordToPdfTool.value;
    const isImage = isImageToPdfTool.value;
    const isPdfSplit = isPdfSplitTool.value;

    const extensions = isWord
      ? ["docx"]
      : isImage
        ? ["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"]
        : ["pdf"];

    const fileTypeName = isWord
      ? "Word 文档"
      : isImage
        ? "图片文件"
        : "PDF 文件";

    const result = await open({
      multiple: !isPdfSplit,
      filters: [
        {
          name: fileTypeName,
          extensions,
        },
      ],
    });

    if (result === null) return;

    const files: string[] =
      typeof result === "string" ? [result] : result;

    if (isPdfSplit) {
      selectedFiles.value = files.slice(0, 1);
    } else {
      // 追加文件时去重
      selectedFiles.value = [
        ...new Set([...selectedFiles.value, ...files]),
      ];
    }

    clearResult();
  } catch (error) {
    statusMessage.value = `选择文件失败：${String(error)}`;
  }
}

/** 选择水印图片 */
async function chooseWatermarkImage() {
  try {
    const result = await open({
      multiple: false,
      filters: [
        {
          name: "水印图片",
          extensions: ["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
        },
      ],
    });

    if (typeof result === "string" && result) {
      watermarkImagePath.value = result;
      clearResult();
    }
  } catch (error) {
    statusMessage.value = `选择水印图片失败：${String(error)}`;
  }
}

/** 选择处理结果的保存目录 */
async function chooseOutputFolder() {
  try {
    const result = await open({
      multiple: false,
      directory: true,
      title: "选择处理结果的保存目录",
    });

    if (typeof result === "string" && result) {
      outputFolder.value = result;
      clearResult();
    }
  } catch (error) {
    statusMessage.value = `选择目录失败：${String(error)}`;
  }
}

/** 从待处理列表中移除文件 */
function removeFile(index: number) {
  selectedFiles.value.splice(index, 1);
  clearResult();
}

/** 清空待处理文件 */
function clearFiles() {
  selectedFiles.value = [];
  clearResult();
}

// #endregion

// #region 输入校验

/**
 * 检查通用文件输入
 *
 * 所有文件处理工具均需要选择输入文件和输出目录。
 */
function validateCommonInputs() {
  const fileType = isWordToPdfTool.value
    ? "Word"
    : isImageToPdfTool.value
      ? "图片"
      : "PDF";

  if (selectedFiles.value.length === 0) {
    statusMessage.value = `请先选择至少一个${fileType}文件。`;
    return false;
  }

  if (isPdfMergeTool.value && selectedFiles.value.length < 2) {
    statusMessage.value = "PDF 合并至少需要选择两个文件。";
    return false;
  }

  if (isPdfSplitTool.value && selectedFiles.value.length !== 1) {
    statusMessage.value = "PDF 拆分一次只能选择一个文件。";
    return false;
  }

  if (!outputFolder.value) {
    statusMessage.value = "请先选择输出目录。";
    return false;
  }

  return true;
}

// #endregion

// #region PDF 解密

/** 清除 PDF 权限限制 */
async function startUnlock() {
  if (isProcessing.value || !validateCommonInputs()) return;

  isProcessing.value = true;
  statusMessage.value = "正在处理 PDF...";
  processResponse.value = null;

  try {
    const raw = await invoke<string>("unlock_pdfs", {
      files: [...selectedFiles.value],
      outputFolder: outputFolder.value,
    });

    const result = JSON.parse(raw) as ProcessResponse;

    processResponse.value = result;

    statusMessage.value =
      result.failed > 0
        ? "处理已完成，部分文件未能处理。"
        : "所有文件均已处理完成。";
  } catch (error) {
    statusMessage.value = `处理失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region PDF 加密

/** 为 PDF 添加打开密码或权限密码 */
async function startProtect() {
  if (isProcessing.value || !validateCommonInputs()) return;

  if (
    (passwordMode.value === "view" || passwordMode.value === "both") &&
    !userPassword.value
  ) {
    statusMessage.value = "请输入打开密码。";
    return;
  }

  if (
    (passwordMode.value === "edit" || passwordMode.value === "both") &&
    !ownerPassword.value
  ) {
    statusMessage.value = "请输入权限密码。";
    return;
  }

  if (
    passwordMode.value === "both" &&
    userPassword.value === ownerPassword.value
  ) {
    statusMessage.value = "打开密码和权限密码不能相同。";
    return;
  }

  isProcessing.value = true;
  statusMessage.value = "正在加密 PDF...";
  processResponse.value = null;

  const results: ResultItem[] = [];

  try {
    for (const inputPath of selectedFiles.value) {
      const baseName =
        fileName(inputPath).replace(/\.pdf$/i, "") || "document";

      const outputPath =
        `${outputFolder.value.replace(/[\\/]+$/, "")}/${baseName}_protected.pdf`;

      try {
        const raw = await invoke<string>("protect_pdf", {
          params: {
            input_path: inputPath,
            output_path: outputPath,
            mode: passwordMode.value,
            user_password:
              passwordMode.value === "edit" ? "" : userPassword.value,
            owner_password: ownerPassword.value,
            allow_print: allowPrint.value,
            allow_copy: allowCopy.value,
            allow_modify: allowModify.value,
          },
        });

        const data = JSON.parse(raw);

        results.push({
          success: data.success === true,
          input: inputPath,
          output: data.output_path || data.output || outputPath,
          message:
            data.message ||
            data.error ||
            (data.success ? "加密成功" : "加密失败"),
        });
      } catch (error) {
        results.push({
          success: false,
          input: inputPath,
          message: String(error),
        });
      }
    }

    const successful = results.filter((item) => item.success).length;

    processResponse.value = {
      success: successful === results.length,
      total: results.length,
      successful,
      failed: results.length - successful,
      results,
    };

    statusMessage.value =
      `处理完成：成功 ${successful} 个，失败 ${results.length - successful} 个。`;
  } catch (error) {
    statusMessage.value = `PDF 加密失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region Word 转 PDF

/** 批量将 Word 文档转换为 PDF */
async function startWordToPdf() {
  if (isProcessing.value || !validateCommonInputs()) return;

  isProcessing.value = true;
  statusMessage.value = "正在转换 Word 文件...";
  processResponse.value = null;

  try {
    const raw = await invoke<string>("word_to_pdf", {
      files: [...selectedFiles.value],
      outputFolder: outputFolder.value,
    });

    const result = JSON.parse(raw) as ProcessResponse;

    processResponse.value = result;

    statusMessage.value =
      `转换完成：成功 ${result.successful} 个，失败 ${result.failed} 个。`;
  } catch (error) {
    statusMessage.value = `Word 转 PDF 失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region PDF 加水印

/** 为 PDF 添加文字水印或图片水印 */
async function startWatermark() {
  if (isProcessing.value || !validateCommonInputs()) return;

  if (watermarkType.value === "text" && !watermarkText.value.trim()) {
    statusMessage.value = "请输入水印文字。";
    return;
  }

  if (watermarkType.value === "image" && !watermarkImagePath.value) {
    statusMessage.value = "请选择水印图片。";
    return;
  }

  if (
    watermarkType.value === "text" &&
    (!Number.isFinite(watermarkFontSize.value) ||
      watermarkFontSize.value <= 0)
  ) {
    statusMessage.value = "字体大小必须大于 0。";
    return;
  }

  if (watermarkType.value === "text" && !selectedFont.value) {
    statusMessage.value = "请先选择水印字体。";
    return;
  }

  if (
    watermarkType.value === "image" &&
    (!Number.isFinite(watermarkImageWidth.value) ||
      watermarkImageWidth.value <= 0)
  ) {
    statusMessage.value = "图片宽度必须大于 0。";
    return;
  }

  isProcessing.value = true;
  statusMessage.value = "正在添加 PDF 水印...";
  processResponse.value = null;

  const results: ResultItem[] = [];

  try {
    for (const inputPath of selectedFiles.value) {
      const baseName =
        fileName(inputPath).replace(/\.pdf$/i, "") || "document";

      const outputPath =
        `${outputFolder.value.replace(/[\\/]+$/, "")}/${baseName}_水印.pdf`;

      const params: Record<string, any> = {
        input_path: inputPath,
        output_path: outputPath,
        watermark_type: watermarkType.value,
        opacity: Number(watermarkOpacity.value),
        rotation: Number(watermarkRotation.value),
        position: watermarkPosition.value,
        layer: watermarkLayer.value,
        page_ranges: watermarkPageRanges.value.trim() || "all",
      };

      if (watermarkType.value === "text") {
        params.text = watermarkText.value.trim();
        params.font_size = Number(watermarkFontSize.value);
        params.color = watermarkColor.value;
        params.font_path = selectedFont.value!.path;
        params.font_index = selectedFont.value!.index;
      } else {
        params.image_path = watermarkImagePath.value;
        params.image_width = Number(watermarkImageWidth.value);
      }

      try {
        const raw = await invoke<string>("add_pdf_watermark", {
          params,
        });

        const data = JSON.parse(raw);

        if (!data.success) {
          throw new Error(data.message || "水印添加失败");
        }

        results.push({
          success: true,
          input: inputPath,
          output: data.output_path || outputPath,
          message:
            data.message ||
            `水印添加成功，共处理 ${data.watermarked_pages ?? 0} 页`,
        });
      } catch (error) {
        results.push({
          success: false,
          input: inputPath,
          message: String(error),
        });
      }
    }

    const successful = results.filter((item) => item.success).length;
    const failed = results.length - successful;

    processResponse.value = {
      success: failed === 0,
      total: results.length,
      successful,
      failed,
      results,
    };

    statusMessage.value =
      `水印处理完成：成功 ${successful} 个，失败 ${failed} 个。`;
  } catch (error) {
    statusMessage.value = `PDF 水印处理失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region PDF 去水印

/**
 * 调用 Tauri 后端执行 PDF 去水印
 *
 * Python 脚本通过 JSON 接收 params，并返回 JSON 字符串。
 */
async function removePdfWatermark(params: RemoveWatermarkParams) {
  const raw = await invoke<string>("remove_pdf_watermark", {
    params,
  });

  return JSON.parse(raw);
}

/**
 * 批量移除 PDF 水印
 *
 * 默认处理咕咕专属水印标记和 Watermark 注释。
 * Stamp 注释和全部注释由用户自行决定是否移除。
 */
async function startRemoveWatermark() {
  if (isProcessing.value || !validateCommonInputs()) return;

  // 至少选择一种处理方式
  if (
    !removeMarkedWatermarks.value &&
    !removeWatermarkAnnotations.value &&
    !removeStampAnnotations.value &&
    !removeAllAnnotations.value
  ) {
    statusMessage.value = "请至少选择一种去水印方式。";
    return;
  }

  isProcessing.value = true;
  statusMessage.value = "正在去除 PDF 水印...";
  processResponse.value = null;

  const results: ResultItem[] = [];

  try {
    for (const inputPath of selectedFiles.value) {
      const baseName =
        fileName(inputPath).replace(/\.pdf$/i, "") || "document";

      const outputPath =
        `${outputFolder.value.replace(/[\\/]+$/, "")}/${baseName}_去水印.pdf`;

      try {
        const params: RemoveWatermarkParams = {
          input_path: inputPath,
          output_path: outputPath,
          page_ranges: removeWatermarkPageRanges.value.trim() || "all",
          password: removeWatermarkPassword.value,
          remove_marked_watermarks: removeMarkedWatermarks.value,
          remove_watermark_annotations: removeWatermarkAnnotations.value,
          remove_stamp_annotations: removeStampAnnotations.value,
          remove_all_annotations: removeAllAnnotations.value,
        };

        const data = await removePdfWatermark(params);

        if (!data.success) {
          throw new Error(data.message || data.error || "PDF 去水印失败");
        }

        results.push({
          success: true,
          input: inputPath,
          output: data.output_path || outputPath,
          message:
            data.message ||
            `去水印成功，共处理 ${data.processed_pages ?? 0} 页`,
        });
      } catch (error) {
        results.push({
          success: false,
          input: inputPath,
          message: String(error),
        });
      }
    }

    const successful = results.filter((item) => item.success).length;
    const failed = results.length - successful;

    processResponse.value = {
      success: failed === 0,
      total: results.length,
      successful,
      failed,
      results,
    };

    statusMessage.value =
      `去水印完成：成功 ${successful} 个，失败 ${failed} 个。`;
  } catch (error) {
    statusMessage.value = `PDF 去水印失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region PDF 压缩

/** 批量压缩 PDF 文件 */
async function startCompress() {
  console.log("压缩输入文件：", selectedFiles.value);
  console.log("压缩输出目录：", outputFolder.value);

  if (isProcessing.value || !validateCommonInputs()) return;

  isProcessing.value = true;
  statusMessage.value = "正在压缩 PDF 文件...";
  processResponse.value = null;

  try {
    const raw = await invoke<string>("compress_pdfs", {
      files: [...selectedFiles.value],
      outputFolder: outputFolder.value,
    });

    const result = JSON.parse(raw) as ProcessResponse;

    processResponse.value = result;

    statusMessage.value =
      `压缩完成：成功 ${result.successful} 个，失败 ${result.failed} 个。`;
  } catch (error) {
    statusMessage.value = `PDF 压缩失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region 图片转 PDF

/** 将选中的图片转换为 PDF */
async function startImagesToPdf() {
  if (isProcessing.value || !validateCommonInputs()) return;

  isProcessing.value = true;
  statusMessage.value = "正在转换图片...";
  processResponse.value = null;

  try {
    const raw = await invoke<string>("images_to_pdf", {
      params: {
        input_paths: [...selectedFiles.value],
        output_dir: outputFolder.value,
        output_name: imagePdfName.value,
        merge: mergeImages.value,
      },
    });

    const data = JSON.parse(raw);

    if (!data.success) {
      throw new Error(data.error || "图片转 PDF 失败");
    }

    const results: ResultItem[] = (data.results || []).map(
      (item: any, index: number) => ({
        success: item.success === true,
        input: item.input || selectedFiles.value[index] || "图片文件",
        output: item.output || "",
        message:
          item.message || (item.success ? "转换成功" : "转换失败"),
      })
    );

    const successful = results.filter((item) => item.success).length;

    processResponse.value = {
      success: successful === results.length,
      total: data.total ?? results.length,
      successful,
      failed: results.length - successful,
      results,
    };

    statusMessage.value =
      `转换完成：成功 ${successful} 个，失败 ${results.length - successful} 个。`;
  } catch (error) {
    statusMessage.value = `图片转 PDF 失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region PDF 转图片

/** 将 PDF 页面转换为图片 */
async function startPdfToImages() {
  if (isProcessing.value || !validateCommonInputs()) return;

  isProcessing.value = true;
  statusMessage.value = "正在转换 PDF 页面...";
  processResponse.value = null;

  try {
    const raw = await invoke<string>("pdf_to_images", {
      params: {
        input_paths: [...selectedFiles.value],
        output_dir: outputFolder.value,
        format: pdfImageFormat.value,
        dpi: pdfImageDpi.value,
        pages: pdfImagePages.value,
      },
    });

    const data = JSON.parse(raw);

    if (!data.success && !data.results) {
      throw new Error(data.error || "PDF 转图片失败");
    }

    const results: ResultItem[] = (data.results || []).map(
      (item: any) => ({
        success: item.success === true,
        input: item.input || "",
        output: item.output_dir || "",
        message: item.success
          ? `转换成功，共生成 ${item.converted_pages} 张图片`
          : item.error || "转换失败",
      })
    );

    const successful =
      data.success_count ??
      results.filter((item) => item.success).length;

    const failed = data.failed_count ?? results.length - successful;

    processResponse.value = {
      success: failed === 0,
      total: data.total ?? results.length,
      successful,
      failed,
      results,
    };

    statusMessage.value =
      `转换完成：成功 ${successful} 个 PDF，失败 ${failed} 个。`;
  } catch (error) {
    statusMessage.value = `PDF 转图片失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region PDF 合并

/** 将多个 PDF 合并为一个文件 */
async function startPdfMerge() {
  if (isProcessing.value || !validateCommonInputs()) return;

  if (selectedFiles.value.length < 2) {
    statusMessage.value = "请至少选择两个 PDF 文件。";
    return;
  }

  if (!mergePdfName.value.trim()) {
    statusMessage.value = "请输入合并后的 PDF 文件名称。";
    return;
  }

  isProcessing.value = true;
  statusMessage.value = "正在合并 PDF 文件...";
  processResponse.value = null;

  try {
    const raw = await invoke<string>("pdf_merge", {
      params: {
        input_paths: [...selectedFiles.value],
        output_dir: outputFolder.value,
        output_name: mergePdfName.value.trim(),
      },
    });

    const data = JSON.parse(raw);

    if (!data.success) {
      throw new Error(data.error || data.message || "PDF 合并失败");
    }

    const output = data.output || "";

    const results: ResultItem[] = [
      {
        success: true,
        input: selectedFiles.value.map(fileName).join("、"),
        output,
        message:
          data.message ||
          `成功合并 ${data.total_files ?? selectedFiles.value.length} 个 PDF，共 ${data.total_pages ?? "未知"} 页`,
      },
    ];

    processResponse.value = {
      success: true,
      total: selectedFiles.value.length,
      successful: selectedFiles.value.length,
      failed: 0,
      results,
    };

    statusMessage.value = data.message || "PDF 合并成功。";
  } catch (error) {
    statusMessage.value = `PDF 合并失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region PDF 拆分

/** 按指定模式拆分 PDF 页面 */
async function startPdfSplit() {
  if (isProcessing.value || !validateCommonInputs()) return;

  if (selectedFiles.value.length !== 1) {
    statusMessage.value = "请选择一个 PDF 文件。";
    return;
  }

  if (!splitPdfName.value.trim()) {
    statusMessage.value = "请输入拆分后的文件名称。";
    return;
  }

  if (splitMode.value === "range" && !splitPageRanges.value.trim()) {
    statusMessage.value = "请输入需要拆分的页码范围。";
    return;
  }

  isProcessing.value = true;
  statusMessage.value = "正在拆分 PDF 文件...";
  processResponse.value = null;

  try {
    const raw = await invoke<string>("pdf_split", {
      params: {
        input_path: selectedFiles.value[0],
        output_dir: outputFolder.value,
        output_name: splitPdfName.value.trim(),
        mode: splitMode.value,
        page_ranges:
          splitMode.value === "range" ? splitPageRanges.value.trim() : "",
      },
    });

    const data = JSON.parse(raw);

    if (!data.success) {
      throw new Error(data.error || data.message || "PDF 拆分失败");
    }

    const results: ResultItem[] = (data.results || []).map(
      (item: any) => ({
        success: item.success === true,
        input: selectedFiles.value[0],
        output: item.output || "",
        message:
          item.message ||
          (item.success ? "拆分成功" : item.error || "拆分失败"),
      })
    );

    const successful = results.filter((item) => item.success).length;
    const failed = results.length - successful;

    processResponse.value = {
      success: failed === 0,
      total: data.split_count ?? results.length,
      successful,
      failed,
      results,
    };

    statusMessage.value =
      data.message ||
      `拆分完成：成功 ${successful} 个，失败 ${failed} 个。`;
  } catch (error) {
    statusMessage.value = `PDF 拆分失败：${String(error)}`;
  } finally {
    isProcessing.value = false;
  }
}

// #endregion

// #region 工具处理入口

/**
 * 根据当前选择的工具，执行对应的处理函数。
 */
function startCurrentTool() {
  if (isEncryptionTool.value) {
    void startProtect();
  } else if (isPermissionTool.value) {
    void startUnlock();
  } else if (isWordToPdfTool.value) {
    void startWordToPdf();
  } else if (isCompressTool.value) {
    void startCompress();
  } else if (isImageToPdfTool.value) {
    void startImagesToPdf();
  } else if (isPdfToImageTool.value) {
    void startPdfToImages();
  } else if (isPdfMergeTool.value) {
    void startPdfMerge();
  } else if (isPdfSplitTool.value) {
    void startPdfSplit();
  } else if (isWatermarkTool.value) {
    void startWatermark();
  } else if (isRemoveWatermarkTool.value) {
    void startRemoveWatermark();
  } else {
    statusMessage.value =
      `${selectedTool.value?.name ?? "该工具"}的处理功能尚未接入。`;
  }
}

// #endregion

// #region 生命周期

onMounted(async () => {
  // 获取应用版本
  try {
    appVersion.value = await getVersion();
  } catch (error) {
    console.error("获取应用版本失败：", error);
    appVersion.value = "未知";
  }

  // 加载系统字体
  await loadSystemFonts();
});

// #endregion
</script>

<template>
  <div class="app-shell">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">
          <img src="/logo.png" alt="咕咕 PDF 工具箱" />
        </div>

        <div class="brand-copy">
          <div class="brand-name">咕咕PDF工具箱</div>
          <div class="brand-subtitle">GUGU PDF TOOLS</div>
        </div>
      </div>

      <div class="nav-group">
        <div class="nav-caption">工作空间</div>

        <button
          class="nav-item"
          :class="{ active: activeCategory === '全部工具' }"
          @click="activeCategory = '全部工具'"
        >
          <span class="nav-icon">
            <Icon icon="tabler:tool" :width="20" :height="20" />
          </span>
          <span>工具箱</span>
        </button>
      </div>

      <div class="nav-group">
        <div class="nav-caption">工具分类</div>

        <button
          v-for="category in categories"
          :key="category"
          class="nav-item"
          :class="{
            active: activeCategory === category && category !== '全部工具'
          }"
          @click="activeCategory = category"
        >
          <span class="nav-icon">
            <Icon
              :icon="
                category === '全部工具'
                  ? 'tabler:apps'
                  : category === '页面处理'
                    ? 'tabler:files'
                    : category === '文件处理'
                      ? 'ri:file-history-line'
                      : 'tabler:shield-lock'
              "
              :width="20"
              :height="20"
            />
          </span>

          <span>{{ category }}</span>
        </button>
      </div>

      <div class="sidebar-footer">
        <div class="footer-list">
          <div
            class="footer-item"
            role="button"
            tabindex="0"
            @click="showDonation = true"
            @keydown.enter="showDonation = true"
            @keydown.space.prevent="showDonation = true"
          >
            <Icon icon="tabler:coffee" :width="12" :height="12" />
            <span>打赏支持</span>
          </div>

          <div
            class="footer-item"
            role="button"
            tabindex="0"
            @click="showAbout = true"
            @keydown.enter="showAbout = true"
            @keydown.space.prevent="showAbout = true"
          >
            <Icon icon="tabler:info-square" :width="12" :height="12" />
            <span>关于我们 ( {{ appVersion }} )</span>
          </div>

          <div
            class="footer-item"
            role="button"
            tabindex="0"
            @click="showFeedback = true"
            @keydown.enter="showFeedback = true"
            @keydown.space.prevent="showFeedback = true"
          >
            <Icon icon="mdi:lightbulb-on-outline" :width="12" :height="12" />
            <span>需求与建议</span>
          </div>

          <div class="footer-item">
            <Icon icon="tabler:discount-check-filled" :width="12" :height="12" />
            <span>留在本地、文件更安全</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主页面 -->
    <main class="main-content">
      <header class="page-header">
        <div class="eyebrow">YOUR LOCAL PDF WORKSPACE</div>

        <div class="page-header-title-row">
          <h1 class="page-header-title">文件处理，更简单</h1>

          <div class="page-header-icons">
            <a
              v-if="githubUrl"
              :href="githubUrl"
              target="_blank"
              rel="noopener noreferrer"
              title="GitHub"
            >
              <Icon icon="akar-icons:github-fill" :width="20" :height="20" />
            </a>

            <a
              v-if="giteeUrl"
              :href="giteeUrl"
              target="_blank"
              rel="noopener noreferrer"
              title="Gitee"
            >
              <Icon icon="simple-icons:gitee" :width="20" :height="20" />
            </a>
          </div>
        </div>

        <p>在本地完成 PDF 文件处理，简单、高效、安全。</p>
      </header>

      <!-- 工具搜索 -->
      <div class="search-bar">
        <span class="search-symbol">
          <Icon icon="tabler:search" :width="20" :height="20" />
        </span>

        <input
          v-model="searchText"
          type="text"
          placeholder="搜索工具名称或功能..."
          aria-label="搜索工具"
        />

        <span class="search-hint">PDF TOOLS</span>
      </div>

      <!-- 工具列表 -->
      <section class="tools-section">
        <div class="section-heading">
          <div>
            <h2>实用工具</h2>
            <p>选择一项操作，开始处理你的文件。</p>
          </div>

          <span class="tool-count">{{ filteredTools.length }} 项工具</span>
        </div>

        <div v-if="filteredTools.length" class="tool-grid">
          <button
            v-for="tool in filteredTools"
            :key="tool.id"
            class="tool-card"
            @click="openTool(tool)"
          >
            <span class="tool-icon" :class="tool.id">
              <Icon :icon="tool.icon" :width="28" :height="28" />
            </span>

            <span class="tool-name">{{ tool.name }}</span>
            <span class="tool-description">{{ tool.description }}</span>

            <span class="tool-card-bottom">
              <span>打开工具</span>

              <span class="card-arrow">
                <Icon icon="tabler:arrow-right" :width="16" :height="16" />
              </span>
            </span>
          </button>
        </div>

        <div v-else class="empty-state">
          没有找到相关工具，试试其他关键词。
        </div>
      </section>

      <footer class="page-footer">
        <span>咕咕 PDF 工具箱</span>
        <span>让技术更贴近生活</span>
      </footer>
    </main>

    <!-- 工具处理弹窗 -->
    <div
      v-if="selectedTool"
      class="modal-backdrop"
      @click.self="closeTool"
      @keydown.esc="closeTool"
    >
      <section
        class="modal"
        :class="{ 'unlock-modal': isSecurityTool }"
        role="dialog"
        aria-modal="true"
        :aria-label="selectedTool.name"
      >
        <header class="modal-header">
          <div class="modal-brand">
            <span class="modal-brand-dot"></span>
            {{ selectedTool.name }}
          </div>

          <button
            class="modal-close"
            aria-label="关闭弹窗"
            :disabled="isProcessing"
            @click="closeTool"
          >
            ×
          </button>
        </header>

        <div class="unlock-content">
          <!-- 工具信息 -->
          <div class="unlock-title-row">
            <div class="unlock-icon">
              <Icon :icon="selectedTool.icon" :width="28" :height="28" />
            </div>

            <div class="unlock-title-copy">
              <h2>{{ selectedTool.name }}</h2>
              <p>{{ selectedTool.description }}</p>
            </div>
          </div>

          <!-- 文件选择 -->
          <div class="unlock-section">
            <div class="section-title-row">
              <span class="step-number">01</span>

              <h3>
                选择
                {{
                  selectedTool?.id === "word_to_pdf"
                    ? "Word"
                    : selectedTool?.id === "image_to_pdf"
                      ? "图片"
                      : "PDF"
                }}
                文件
              </h3>
            </div>

            <p class="section-description">
              {{
                selectedTool?.id === "word_to_pdf"
                  ? "支持一次添加多个 DOCX 文件。"
                  : selectedTool?.id === "image_to_pdf"
                    ? "支持一次添加多个 PNG、JPG、WEBP、BMP、TIFF 等图片文件。"
                    : isPdfSplitTool
                      ? "请选择一个 PDF 文件进行拆分。"
                      : "支持一次添加多个 PDF 文件。"
              }}
            </p>

            <!-- 尚未选择文件 -->
            <div
              v-if="selectedFiles.length === 0"
              class="file-empty"
              :class="{ disabled: isProcessing }"
              @click="!isProcessing && chooseFiles()"
            >
              <div class="empty-file-icon">
                <Icon icon="tabler:file-upload" :width="24" :height="24" />
              </div>

              <div class="empty-file-title">
                点击选择
                {{
                  selectedTool?.id === "word_to_pdf"
                    ? "Word"
                    : selectedTool?.id === "image_to_pdf"
                      ? "图片"
                      : "PDF"
                }}
                文件
              </div>

              <div class="empty-file-description">
                支持多选
                {{
                  selectedTool?.id === "word_to_pdf"
                    ? "DOCX"
                    : selectedTool?.id === "image_to_pdf"
                      ? "PNG、JPG、WEBP、BMP、TIFF"
                      : "PDF"
                }}
                文件，点击此区域即可添加
              </div>
            </div>

            <!-- 已选择文件 -->
            <div v-else class="file-list">
              <div
                v-for="(file, index) in selectedFiles"
                :key="file"
                class="file-item"
              >
                <div class="file-type-icon">
                  {{
                    selectedTool?.id === "word_to_pdf"
                      ? "DOCX"
                      : selectedTool?.id === "image_to_pdf"
                        ? "Image"
                        : "PDF"
                  }}
                </div>

                <div class="file-info">
                  <div class="file-name" :title="file">
                    {{ fileName(file) }}
                  </div>

                  <div class="file-path" :title="file">
                    {{ file }}
                  </div>
                </div>

                <button
                  class="remove-file"
                  :disabled="isProcessing"
                  aria-label="移除此文件"
                  @click="removeFile(index)"
                >
                  ×
                </button>
              </div>
            </div>

            <!-- 文件列表操作 -->
            <div v-if="selectedFiles.length > 0" class="file-actions">
              <button
                class="button button-secondary"
                :disabled="isProcessing"
                @click="chooseFiles"
              >
                <span>＋</span>
                继续添加文件
              </button>

              <button
                class="text-button"
                :disabled="isProcessing"
                @click="clearFiles"
              >
                清空列表
              </button>
            </div>
          </div>

          <!-- 输出目录 -->
          <div class="unlock-section">
            <div class="section-title-row">
              <span class="step-number">02</span>
              <h3>设置保存位置</h3>
            </div>

            <p class="section-description">
              处理后的文件将保存到指定目录。
            </p>

            <div class="folder-picker">
              <div class="folder-icon">
                <Icon icon="tabler:folder-open" :width="24" :height="24" />
              </div>

              <div class="folder-info">
                <div class="folder-label">输出目录</div>

                <div
                  class="folder-path"
                  :title="outputFolder || '请选择文件保存位置'"
                >
                  {{ outputFolder || "请选择文件保存位置" }}
                </div>
              </div>

              <button
                class="button button-secondary folder-button"
                :disabled="isProcessing"
                @click="chooseOutputFolder"
              >
                浏览
              </button>
            </div>
          </div>

          <!-- 图片转 PDF 参数 -->
          <div v-if="isImageToPdfTool" class="unlock-section">
            <div class="section-title-row">
              <span class="step-number">03</span>
              <h3>转换设置</h3>
            </div>

            <label class="password-label">转换模式</label>

            <div class="permission-options">
              <label>
                <input
                  v-model="mergeImages"
                  type="radio"
                  :value="true"
                  :disabled="isProcessing"
                />
                多张图片合并为一个 PDF
              </label>

              <label>
                <input
                  v-model="mergeImages"
                  type="radio"
                  :value="false"
                  :disabled="isProcessing"
                />
                每张图片单独生成 PDF
              </label>
            </div>

            <div v-if="mergeImages">
              <label class="password-label" for="image-pdf-name">
                PDF 文件名称
              </label>

              <input
                id="image-pdf-name"
                v-model="imagePdfName"
                type="text"
                placeholder="例如：图片合并"
                :disabled="isProcessing"
              />
            </div>
          </div>

          <!-- PDF 转图片参数 -->
          <div v-if="isPdfToImageTool" class="unlock-section">
            <div class="section-title-row">
              <span class="step-number">03</span>
              <h3>转换设置</h3>
            </div>

            <label class="password-label" for="pdf-image-format">
              图片格式
            </label>

            <div class="password-mode-wrapper">
              <select
                id="pdf-image-format"
                v-model="pdfImageFormat"
                class="password-mode-select"
                :disabled="isProcessing"
              >
                <option value="png">PNG（无损）</option>
                <option value="jpg">JPG（体积较小）</option>
              </select>

              <span class="password-mode-arrow" aria-hidden="true"></span>
            </div>

            <label class="password-label" for="pdf-image-dpi">
              图片分辨率
            </label>

            <div class="password-mode-wrapper">
              <select
                id="pdf-image-dpi"
                v-model.number="pdfImageDpi"
                class="password-mode-select"
                :disabled="isProcessing"
              >
                <option :value="72">72 DPI（快速）</option>
                <option :value="150">150 DPI（普通）</option>
                <option :value="200">200 DPI（清晰）</option>
                <option :value="300">300 DPI（高清）</option>
              </select>

              <span class="password-mode-arrow" aria-hidden="true"></span>
            </div>

            <label class="password-label" for="pdf-image-pages">
              转换页码
            </label>

            <input
              id="pdf-image-pages"
              v-model="pdfImagePages"
              type="text"
              placeholder="留空表示全部页面，例如：1-3,5,8-10"
              :disabled="isProcessing"
            />

            <p class="section-description">
              页码从 1 开始，支持单页和连续范围。多个页码用英文逗号分隔。
            </p>
          </div>

          <!-- PDF 合并参数 -->
          <div v-if="isPdfMergeTool" class="unlock-section">
            <div class="section-title-row">
              <span class="step-number">03</span>
              <h3>合并设置</h3>
            </div>

            <label class="password-label" for="merge-pdf-name">
              输出文件名称
            </label>

            <input
              id="merge-pdf-name"
              v-model="mergePdfName"
              type="text"
              placeholder="例如：合并文件"
              :disabled="isProcessing"
            />

            <p class="section-description">
              按照上方文件列表的顺序合并 PDF 文件。
            </p>
          </div>

          <!-- PDF 拆分参数 -->
          <div v-if="isPdfSplitTool" class="unlock-section">
            <div class="section-title-row">
              <span class="step-number">03</span>
              <h3>拆分设置</h3>
            </div>

            <label class="password-label" for="split-pdf-name">
              输出文件名称
            </label>

            <input
              id="split-pdf-name"
              v-model="splitPdfName"
              type="text"
              placeholder="例如：拆分文件"
              :disabled="isProcessing"
            />

            <label class="password-label" for="split-mode">
              拆分模式
            </label>

            <div class="password-mode-wrapper">
              <select
                id="split-mode"
                v-model="splitMode"
                class="password-mode-select"
                :disabled="isProcessing"
              >
                <option value="each">每页拆分成一个 PDF</option>
                <option value="range">按指定页码范围拆分</option>
              </select>

              <span class="password-mode-arrow" aria-hidden="true"></span>
            </div>

            <div v-if="splitMode === 'range'">
              <label class="password-label" for="split-page-ranges">
                页码范围
              </label>

              <input
                id="split-page-ranges"
                v-model="splitPageRanges"
                type="text"
                placeholder="例如：1-3,4-8,9-12"
                :disabled="isProcessing"
              />

              <p class="section-description">
                页码从 1 开始，多个范围使用英文逗号分隔。
                例如 1-3,4-8,9-12。
              </p>
            </div>
          </div>

          <!-- PDF 去水印说明 -->
          <div
            v-if="selectedTool?.id === 'remove_watermark'"
            class="unlock-section"
          >
            <div class="section-title-row">
              <span class="step-number">03</span>
              <h3>去水印说明</h3>
            </div>

            <p class="section-description">
              该工具会根据 PDF 中可识别的水印对象和水印注释进行处理。
              不保证能够移除已经与页面内容合并的水印。
            </p>

            <div class="permission-options">
              <label>
                <input type="checkbox" checked disabled />
                移除可识别的水印标记
              </label>

              <label>
                <input type="checkbox" checked disabled />
                移除水印类型注释
              </label>
            </div>

            <p class="section-description">
              普通文本、图片及其他页面内容不会作为普通注释被全部删除。
              处理结果请逐页检查。
            </p>
          </div>

          <!-- PDF 水印参数 -->
          <div v-if="isWatermarkTool" class="unlock-section">
            <div class="section-title-row">
              <span class="step-number">03</span>
              <h3>水印设置</h3>
            </div>

            <!-- 水印类型 -->
            <label class="password-label">水印类型</label>

            <div class="password-mode-wrapper">
              <select
                v-model="watermarkType"
                class="password-mode-select"
                :disabled="isProcessing"
              >
                <option value="text">文字水印</option>
                <option value="image">图片水印</option>
              </select>

              <span class="password-mode-arrow"></span>
            </div>

            <!-- 文字水印 -->
            <template v-if="watermarkType === 'text'">
              <label class="password-label" for="watermark-text">
                水印文字
              </label>

              <input
                id="watermark-text"
                v-model="watermarkText"
                type="text"
                placeholder="例如：内部资料"
                :disabled="isProcessing"
              />

              <label class="password-label" for="watermark-font-size">
                字体大小
              </label>

              <input
                id="watermark-font-size"
                v-model.number="watermarkFontSize"
                type="number"
                min="1"
                placeholder="48"
                :disabled="isProcessing"
              />

              <label class="password-label" for="watermark-color">
                水印颜色
              </label>

              <input
                id="watermark-color"
                v-model="watermarkColor"
                type="color"
                :disabled="isProcessing"
              />

              <label class="password-label" for="watermark-font-path">
                水印字体
              </label>

              <div class="password-mode-wrapper">
                <select
                  id="watermark-font-path"
                  v-model="selectedFontKey"
                  class="password-mode-select"
                  :disabled="
                    isProcessing ||
                    isLoadingFonts ||
                    systemFonts.length === 0
                  "
                >
                  <option value="" disabled>
                    {{
                      isLoadingFonts
                        ? "正在获取系统字体..."
                        : systemFonts.length > 0
                          ? "请选择字体"
                          : "没有检测到系统字体"
                    }}
                  </option>

                  <option
                    v-for="font in systemFonts"
                    :key="`${font.path}-${font.index}`"
                    :value="`${font.path}::${font.index}`"
                  >
                    {{ font.name }}
                  </option>
                </select>

                <span class="password-mode-arrow" aria-hidden="true"></span>

                <div class="font-preview">
                  <div class="font-preview-label">字体效果预览</div>

                  <div
                    class="font-preview-content"
                    :style="{
                      fontFamily: selectedFont
                        ? `'${selectedFont.name}', sans-serif`
                        : 'sans-serif'
                    }"
                  >
                    {{ fontPreviewText }}
                  </div>

                  <div class="font-preview-name">
                    {{ selectedFont?.name ?? "请选择字体" }}
                  </div>
                </div>
              </div>
            </template>

            <!-- 图片水印 -->
            <template v-else>
              <label class="password-label">水印图片</label>

              <div class="folder-picker">
                <div class="folder-icon">
                  <Icon icon="tabler:photo" :width="24" :height="24" />
                </div>

                <div class="folder-info">
                  <div class="folder-label">图片路径</div>

                  <div
                    class="folder-path"
                    :title="watermarkImagePath"
                  >
                    {{ watermarkImagePath || "请选择水印图片" }}
                  </div>
                </div>

                <button
                  class="button button-secondary folder-button"
                  :disabled="isProcessing"
                  @click="chooseWatermarkImage"
                >
                  浏览
                </button>
              </div>

              <label class="password-label" for="watermark-image-width">
                图片宽度（PDF 点）
              </label>

              <input
                id="watermark-image-width"
                v-model.number="watermarkImageWidth"
                type="number"
                min="1"
                placeholder="150"
                :disabled="isProcessing"
              />
            </template>

            <!-- 公共参数 -->
            <label class="password-label" for="watermark-opacity">
              透明度（0～1）
            </label>

            <input
              id="watermark-opacity"
              v-model.number="watermarkOpacity"
              type="number"
              min="0"
              max="1"
              step="0.05"
              :disabled="isProcessing"
            />

            <label class="password-label" for="watermark-rotation">
              旋转角度
            </label>

            <input
              id="watermark-rotation"
              v-model.number="watermarkRotation"
              type="number"
              placeholder="45"
              :disabled="isProcessing"
            />

            <label class="password-label">水印位置</label>

            <div class="permission-options">
              <label>
                <input
                  v-model="watermarkPosition"
                  type="radio"
                  value="center"
                  :disabled="isProcessing"
                />
                页面居中
              </label>

              <label>
                <input
                  v-model="watermarkPosition"
                  type="radio"
                  value="tile"
                  :disabled="isProcessing"
                />
                全页平铺
              </label>
            </div>

            <label class="password-label">水印层级</label>

            <div class="permission-options">
              <label>
                <input
                  v-model="watermarkLayer"
                  type="radio"
                  value="foreground"
                  :disabled="isProcessing"
                />
                页面上方
              </label>

              <label>
                <input
                  v-model="watermarkLayer"
                  type="radio"
                  value="background"
                  :disabled="isProcessing"
                />
                页面下方
              </label>
            </div>

            <label class="password-label" for="watermark-pages">
              指定页面范围
            </label>

            <input
              id="watermark-pages"
              v-model="watermarkPageRanges"
              type="text"
              placeholder="all 或 1-3,5,8-10"
              :disabled="isProcessing"
            />

            <p class="section-description">
              留空或填写 all 表示全部页面。页码从 1 开始，支持单页、连续范围和组合范围。
            </p>
          </div>

          <!-- PDF 密码设置 -->
          <div v-if="isEncryptionTool" class="unlock-section">
            <div class="section-title-row">
              <span class="step-number">03</span>
              <h3>密码设置</h3>
            </div>

            <label class="password-label" for="password-mode">
              加密模式
            </label>

            <div class="password-mode-wrapper">
              <select
                id="password-mode"
                v-model="passwordMode"
                class="password-mode-select"
                :disabled="isProcessing"
              >
                <option value="view">打开密码</option>
                <option value="edit">权限密码</option>
                <option value="both">打开密码 + 权限密码</option>
              </select>

              <span class="password-mode-arrow" aria-hidden="true"></span>
            </div>

            <div v-if="passwordMode !== 'edit'">
              <label class="password-label" for="user-password">
                打开密码
              </label>

              <input
                id="user-password"
                v-model="userPassword"
                type="password"
                placeholder="请输入打开 PDF 的密码"
                :disabled="isProcessing"
              />
            </div>

            <div v-if="passwordMode !== 'view'">
              <label class="password-label" for="owner-password">
                权限密码
              </label>

              <input
                id="owner-password"
                v-model="ownerPassword"
                type="password"
                placeholder="请输入权限密码"
                :disabled="isProcessing"
              />
            </div>

            <div
              v-if="passwordMode !== 'view'"
              class="permission-options"
            >
              <label>
                <input
                  v-model="allowPrint"
                  type="checkbox"
                  :disabled="isProcessing"
                />
                允许打印
              </label>

              <label>
                <input
                  v-model="allowCopy"
                  type="checkbox"
                  :disabled="isProcessing"
                />
                允许复制内容
              </label>

              <label>
                <input
                  v-model="allowModify"
                  type="checkbox"
                  :disabled="isProcessing"
                />
                允许修改内容
              </label>
            </div>
          </div>

          <!-- 处理状态 -->
          <div
            v-if="statusMessage"
            class="status-message"
            role="status"
            aria-live="polite"
          >
            <span class="status-message-icon">
              {{ processResponse && processResponse.failed === 0 ? "✓" : "i" }}
            </span>

            <span>{{ statusMessage }}</span>
          </div>

          <!-- 处理结果 -->
          <div v-if="processResponse" class="result-panel">
            <div class="result-heading">
              <span
                class="result-check"
                :class="{ 'error-text': processResponse.failed > 0 }"
              >
                {{ processResponse.failed > 0 ? "!" : "✓" }}
              </span>

              <strong>
                {{
                  processResponse.failed === 0
                    ? "处理完成"
                    : processResponse.successful > 0
                      ? "部分文件处理失败"
                      : "处理失败"
                }}
              </strong>
            </div>

            <div class="result-stats">
              <div class="result-stat">
                <span class="stat-value">
                  {{ processResponse.total }}
                </span>
                <span class="stat-label">总文件数</span>
              </div>

              <div class="result-stat">
                <span class="stat-value success-text">
                  {{ processResponse.successful }}
                </span>
                <span class="stat-label">处理成功</span>
              </div>

              <div class="result-stat">
                <span
                  class="stat-value"
                  :class="{ 'error-text': processResponse.failed > 0 }"
                >
                  {{ processResponse.failed }}
                </span>
                <span class="stat-label">处理失败</span>
              </div>
            </div>

            <div class="result-list">
              <div
                v-for="(item, index) in processResponse.results"
                :key="`${item.input}-${index}`"
                class="result-item"
              >
                <span
                  class="result-item-status"
                  :class="item.success ? 'result-ok' : 'result-failed'"
                >
                  {{ item.success ? "✓" : "!" }}
                </span>

                <div class="result-item-info">
                  <div class="result-item-name" :title="item.input">
                    {{ fileName(item.input) }}
                  </div>

                  <div class="result-item-message">
                    {{ item.message }}

                    <span v-if="item.output">
                      · 输出：{{ fileName(item.output) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 工具说明 -->
          <div class="unlock-note">
            <span>
              <Icon icon="tabler:info-circle" :width="16" :height="16" />
            </span>

            <span>
              {{
                isEncryptionTool
                  ? "设置打开密码或权限密码，保护 PDF 文件内容和操作权限。"
                  : isPermissionTool
                    ? "仅处理具有相应权限的 PDF 文件。请确认你有权修改这些文件。"
                    : isCompressTool
                      ? "支持批量压缩 PDF 文件，处理后的文件将保存到指定目录。压缩效果取决于 PDF 文件的内容。"
                      : isWordToPdfTool
                        ? "支持将 DOCX 文档转换为 PDF，转换后的文件将保存到指定目录。"
                        : isImageToPdfTool
                          ? "支持 JPG、PNG、BMP、WEBP、TIFF 图片，可选择合并为一个 PDF 或分别生成 PDF。"
                          : isPdfToImageTool
                            ? "支持 PNG、JPG 格式，可设置分辨率和指定转换页码。"
                            : isPdfMergeTool
                              ? "支持将多个 PDF 文件合并为一个 PDF，可以自定义输出文件名称。"
                              : isPdfSplitTool
                                ? "支持将 PDF 逐页拆分，或按照指定页码范围拆分成多个 PDF 文件。"
                                : isWatermarkTool
                                  ? "支持文字和图片水印，可设置透明度、旋转角度、位置、层级及指定页面范围。"
                                  : selectedTool?.id === "remove_watermark"
                                    ? "尝试移除 PDF 中可识别的水印对象和水印注释。已经与页面内容合并的水印可能无法移除。"
                                    : "请选择文件和输出目录后开始处理。"
              }}
            </span>
          </div>

          <!-- 弹窗操作 -->
          <footer class="unlock-footer">
            <button
              class="button button-secondary cancel-button"
              :disabled="isProcessing"
              @click="closeTool"
            >
              关闭
            </button>

            <button
              class="button button-primary"
              :disabled="
                isProcessing ||
                selectedFiles.length === 0 ||
                !outputFolder ||
                !canProcess
              "
              @click="startCurrentTool"
            >
              <span v-if="isProcessing" class="loading-spinner"></span>

              <span v-else class="spinner">
                <Icon icon="ic:round-not-started" :width="14" :height="14" />
              </span>

              <span>
                {{
                  isProcessing
                    ? (isEncryptionTool ? "正在加密..." : "正在处理...")
                    : selectedFiles.length === 0
                      ? "请选择文件"
                      : !outputFolder
                        ? "请选择输出目录"
                        : !canProcess
                          ? "请完善处理参数"
                          : isEncryptionTool
                            ? "开始加密"
                            : "开始处理"
                }}
              </span>
            </button>
          </footer>
        </div>
      </section>
    </div>
  </div>

  <!-- 打赏弹窗 -->
  <Teleport to="body">
    <div
      v-if="showDonation"
      class="donation-mask"
      @click.self="showDonation = false"
    >
      <div class="donation-card" role="dialog" aria-modal="true">
        <button
          class="donation-close"
          aria-label="关闭"
          @click="showDonation = false"
        >
          <Icon icon="tabler:x" :width="18" :height="18" />
        </button>

        <div class="donation-icon">
          <Icon icon="tabler:coffee" :width="28" :height="28" />
        </div>

        <h3>打赏支持</h3>

        <p>
          如果这个工具对你有帮助，欢迎支持我们继续改进。感恩的心~
        </p>

        <div class="donation-placeholder">
          <small>
            <img
              src="/pay_code.png"
              alt="打赏二维码"
              class="donation-qr"
            />
          </small>
        </div>

        <button
          class="donation-confirm"
          @click="showDonation = false"
        >
          知道了
        </button>
      </div>
    </div>
  </Teleport>

  <!-- 关于我们弹窗 -->
  <Teleport to="body">
    <div
      v-if="showAbout"
      class="about-mask"
      @click.self="showAbout = false"
      @keydown.esc="showAbout = false"
    >
      <div
        class="about-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-title"
      >
        <button
          class="about-close"
          aria-label="关闭"
          @click="showAbout = false"
        >
          <Icon icon="tabler:x" :width="18" :height="18" />
        </button>

        <!-- 项目信息 -->
        <div class="about-header">
          <div class="about-logo">
            <img
              src="/logo.png"
              alt="咕咕 PDF 工具箱"
              style="width: 100%; height: 100%;"
            />
          </div>

          <h3 id="about-title">咕咕 PDF 工具箱</h3>

          <p class="about-subtitle">
            简单、实用的桌面 PDF 工具
          </p>

          <span class="about-version">
            当前版本 {{ appVersion }}
          </span>
        </div>

        <!-- 更新设置 -->
        <div class="about-update">
          <button
            @click="checkUpdate"
            :disabled="checkingUpdate"
          >
            <Icon icon="tabler:refresh" :width="15" />
            {{ checkingUpdate ? "检查中..." : "检查更新" }}
          </button>

          <label>
            <input
              v-model="autoCheckUpdate"
              type="checkbox"
            />
            有更新自动弹窗
          </label>
        </div>

        <div class="about-content">
          <!-- 项目仓库 -->
          <section class="about-section">
            <h4>
              <Icon icon="tabler:git-branch" :width="16" :height="16" />
              项目仓库
            </h4>

            <div class="about-links">
              <button
                class="about-link"
                :disabled="!githubUrl"
                @click="openExternalLink(githubUrl)"
              >
                <Icon icon="tabler:brand-github" :width="18" :height="18" />
                <span>GitHub</span>
                <Icon icon="tabler:external-link" :width="14" :height="14" />
              </button>

              <button
                class="about-link"
                :disabled="!giteeUrl"
                @click="openExternalLink(giteeUrl)"
              >
                <Icon icon="ri:gitee-line" :width="18" :height="18" />
                <span>Gitee</span>
                <Icon icon="tabler:external-link" :width="14" :height="14" />
              </button>
            </div>

            <p
              v-if="!githubUrl && !giteeUrl"
              class="about-hint"
            >
              仓库地址尚未配置
            </p>
          </section>

          <!-- 参与人员 -->
          <section class="about-section">
            <h4>
              <Icon icon="tabler:users" :width="16" :height="16" />
              参与人员
            </h4>

            <div class="about-members">
              <div
                v-for="(member, index) in teamMembers"
                :key="`${member.role}-${index}`"
                class="about-member"
              >
                <span class="member-avatar">
                  <Icon icon="tabler:user" :width="18" :height="18" />
                </span>

                <span class="member-name">
                  {{ member.name }}
                </span>

                <span class="member-role">
                  {{ member.role }}
                </span>
              </div>
            </div>
          </section>

          <!-- 技术栈 -->
          <section class="about-section">
            <h4>
              <Icon icon="tabler:code" :width="16" :height="16" />
              技术栈
            </h4>

            <div class="about-tags">
              <span>Vue 3</span>
              <span>TypeScript</span>
              <span>Tauri 2</span>
              <span>Rust</span>
              <span>Iconify</span>
              <span>Python</span>
            </div>
          </section>

          <!-- 技术实现 -->
          <section class="about-section">
            <h4>
              <Icon icon="tabler:settings-code" :width="16" :height="16" />
              技术实现
            </h4>

            <div class="about-tech-list">
              <div class="about-tech-item">
                <span class="about-tech-name">界面层</span>
                <span class="about-tech-desc">Vue 3 + TypeScript</span>
              </div>

              <div class="about-tech-item">
                <span class="about-tech-name">桌面框架</span>
                <span class="about-tech-desc">Tauri 2</span>
              </div>

              <div class="about-tech-item">
                <span class="about-tech-name">原生后端</span>
                <span class="about-tech-desc">Rust</span>
              </div>

              <div class="about-tech-item">
                <span class="about-tech-name">图标组件</span>
                <span class="about-tech-desc">Iconify Vue</span>
              </div>

              <div class="about-tech-item">
                <span class="about-tech-name">文件处理</span>
                <span class="about-tech-desc">
                  以实际使用的处理工具为准
                </span>
              </div>
            </div>

            <p class="about-hint">
              具体处理流程和功能以软件实际实现为准。
            </p>
          </section>

          <!-- 开源项目致谢 -->
          <section class="about-section">
            <h4>
              <Icon icon="tabler:heart-handshake" :width="16" :height="16" />
              开源项目致谢
            </h4>

            <p class="about-thanks-text">
              感谢开源社区的开发者与维护者。
              感谢这些优秀的项目为软件开发提供的技术支持。
            </p>

            <div class="about-opensource-list">
              <div
                v-for="project in openSourceProjects"
                :key="project.name"
                class="about-opensource-item"
              >
                <div class="about-opensource-info">
                  <span class="about-opensource-name">
                    {{ project.name }}
                  </span>

                  <span class="about-opensource-desc">
                    {{ project.description }}
                  </span>
                </div>

                <button
                  class="about-repo-link"
                  @click="openExternalLink(project.url)"
                >
                  项目主页
                  <Icon icon="tabler:external-link" :width="13" :height="13" />
                </button>
              </div>
            </div>

            <p class="about-hint">
              各第三方项目的版权及许可证以其官方声明为准。
            </p>
          </section>

          <!-- 项目说明 -->
          <section class="about-section about-description">
            <h4>
              <Icon icon="tabler:info-circle" :width="16" :height="16" />
              关于项目
            </h4>

            <p>
              咕咕 PDF 工具箱是一款桌面文件处理工具，
              致力于提供简洁、便捷的 PDF 处理体验。
            </p>

            <p>
              软件的实际功能、文件处理方式及隐私保护情况，
              以当前版本的实现为准。
            </p>
          </section>
        </div>

        <!-- 弹窗底部 -->
        <div class="about-footer">
          <span>
            我们是技术的翻译者，让复杂变简单，让技术更贴近生活。
          </span>

          <button @click="showAbout = false">
            关闭
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 需求与建议弹窗 -->
  <Teleport to="body">
    <Transition name="feedback-dialog">
      <div
        v-if="showFeedback"
        class="feedback-mask"
        @click.self="showFeedback = false"
      >
        <div class="feedback-dialog">
          <div class="feedback-header">
            <div>
              <h3>需求与建议</h3>
              <p>请选择你希望使用的反馈平台</p>
            </div>

            <button
              class="feedback-close"
              @click="showFeedback = false"
            >
              ×
            </button>
          </div>

          <div class="feedback-options">
            <!-- Gitee -->
            <button
              class="feedback-option"
              @click="openFeedback('gitee')"
            >
              <div class="feedback-icon gitee-icon">
                <Icon icon="simple-icons:gitee" :width="28" :height="28" />
              </div>

              <div class="feedback-info">
                <span class="feedback-name">Gitee</span>
                <span class="feedback-desc">国内推荐访问 · 码云</span>
              </div>

              <span class="feedback-arrow">›</span>
            </button>

            <!-- GitHub -->
            <button
              class="feedback-option"
              @click="openFeedback('github')"
            >
              <div class="feedback-icon github-icon">
                <Icon icon="akar-icons:github-fill" :width="28" :height="28" />
              </div>

              <div class="feedback-info">
                <span class="feedback-name">GitHub</span>
                <span class="feedback-desc">海外推荐访问 · GitHub</span>
              </div>

              <span class="feedback-arrow">›</span>
            </button>
          </div>

          <div class="feedback-footer">
            欢迎提交功能建议或反馈软件问题
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- 更新弹窗 -->
  <Teleport to="body">
    <div
      v-if="showUpdateDialog"
      class="donation-mask update-mask"
      @click.self="showUpdateDialog = false"
    >
      <div
        class="donation-card update-dialog"
        role="dialog"
        aria-modal="true"
      >
        <button
          class="donation-close"
          aria-label="关闭"
          @click="showUpdateDialog = false"
        >
          <Icon icon="tabler:x" :width="18" :height="18" />
        </button>

        <div class="donation-icon">
          <Icon
            :icon="
              updateStatus === 'available'
                ? 'tabler:download'
                : updateStatus === 'downloading'
                  ? 'tabler:refresh'
                  : 'tabler:check'
            "
            :width="28"
            :height="28"
          />
        </div>

        <h3>{{ updateTitle }}</h3>

        <p>{{ updateMessage }}</p>

        <!-- 发现新版本 -->
        <div
          v-if="updateStatus === 'available'"
          class="update-info"
        >
          <div class="update-version">
            <span>当前版本</span>
            <span>{{ appVersion }}</span>
          </div>

          <div class="update-version">
            <span>最新版本</span>
            <span>{{ latestVersion }}</span>
          </div>

          <div
            v-if="updateNotes"
            class="update-notes"
          >
            <strong>更新内容</strong>
            <p>{{ updateNotes }}</p>
          </div>
        </div>

        <!-- 下载进度 -->
        <div
          v-if="updateStatus === 'downloading'"
          class="update-progress"
        >
          <div class="progress-track">
            <div
              class="progress-value"
              :style="{ width: downloadProgress + '%' }"
            ></div>
          </div>

          <small>{{ downloadProgress }}%</small>
        </div>

        <!-- 操作按钮 -->
        <button
          v-if="updateStatus === 'available'"
          class="donation-confirm"
          @click="startUpdate"
        >
          立即更新
        </button>

        <button
          v-else-if="updateStatus === 'downloading'"
          class="donation-confirm"
          disabled
        >
          正在下载...
        </button>

        <button
          v-else
          class="donation-confirm"
          @click="showUpdateDialog = false"
        >
          知道了
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style>
/* =========================================================
   01. 全局基础样式
   ========================================================= */

:root {
  font-family:
    Inter,
    "Microsoft YaHei",
    "PingFang SC",
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;

  color: #253249;
  background: #f7f8fb;
  font-size: 14px;

  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

* {
  box-sizing: border-box;
  -webkit-user-select: none;
  user-select: none;
}

body {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
}

button,
input,
select,
textarea {
  font: inherit;
}

button {
  -webkit-tap-highlight-color: transparent;
}

button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: 3px solid rgba(49, 94, 231, 0.22);
  outline-offset: 2px;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* 输入内容允许选择和复制 */

input,
textarea,
select,
.file-name,
.file-path,
.folder-path,
.result-item-name,
.result-item-message,
.update-notes p {
  -webkit-user-select: text;
  user-select: text;
}

/* =========================================================
   02. 主界面布局
   ========================================================= */

.app-shell {
  display: flex;
  min-height: 100vh;
  background: #f8f9fc;
}

.main-content {
  display: flex;
  flex-direction: column;
  width: calc(100% - 248px);
  min-width: 0;
  min-height: 100vh;
  padding: 48px 48px 20px;
  margin-left: 248px;
}

/* =========================================================
   03. 左侧导航栏
   ========================================================= */

.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 2;

  display: flex;
  flex-direction: column;

  width: 248px;
  padding: 28px 18px 16px;

  background: #fff;
  border-right: 1px solid #edf0f5;
}

/* 品牌信息 */

.brand {
  display: flex;
  align-items: center;
  gap: 11px;

  padding: 2px 7px 34px;
}

.brand-logo {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  place-items: center;

  overflow: hidden;
  background: #315ee7;
  border-radius: 12px;
}

.brand-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.brand-name {
  color: #26354c;
  font-size: 16px;
  font-weight: 750;
}

.brand-subtitle {
  margin-top: 4px;
  color: #9aa4b4;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1.3px;
}

/* 导航菜单 */

.nav-group {
  margin-bottom: 20px;
}

.nav-caption {
  padding: 0 11px;
  margin-bottom: 10px;

  color: #98a2b3;
  font-size: 11px;
  letter-spacing: 0.5px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 13px;

  width: 100%;
  min-height: 47px;
  padding: 0 13px;
  margin-bottom: 5px;

  color: #617089;
  background: transparent;
  border: 0;
  border-radius: 11px;

  text-align: left;
  cursor: pointer;

  transition:
    background 0.15s,
    color 0.15s;
}

.nav-item:hover {
  color: #315ee7;
  background: #f5f7fc;
}

.nav-item.active {
  color: #315ee7;
  background: #edf2ff;
  font-weight: 650;
}

.nav-icon {
  display: grid;
  width: 22px;
  flex: 0 0 22px;
  place-items: center;
}

/* 导航栏底部 */

.sidebar-footer {
  padding: 17px 8px 3px;
  margin-top: auto;

  color: #7c8798;
  border-top: 1px solid #edf0f4;
  font-size: 10px;
}

.footer-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.footer-item {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.footer-item:hover {
  color: #315ee7;
}

/* =========================================================
   04. 页面标题与搜索区域
   ========================================================= */

/* 页面标题 */

.page-header .eyebrow {
  color: #315ee7;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.8px;
}

.page-header-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.page-header-title-row h1 {
  margin: 15px 0 10px;

  color: #202d42;
  font-size: clamp(27px, 3vw, 36px);
  font-weight: 800;
  letter-spacing: -1.2px;
}

/* 标题右侧图标 */

.page-header-icons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-header-icons a {
  display: inline-flex;
  align-items: center;
  justify-content: center;

  color: #8490a3;
  text-decoration: none;

  transition: transform 0.2s ease;
}

.page-header-icons a:hover,
.page-header-icons a:focus,
.page-header-icons a:active {
  color: #8490a3;
}

.page-header-icons a:hover {
  transform: translateY(-2px);
}

/* 页面介绍 */

.page-header p {
  margin: 0;

  color: #8490a3;
  font-size: 13px;
  line-height: 1.8;
}

/* 搜索框 */

.search-bar {
  display: flex;
  align-items: center;
  gap: 12px;

  min-height: 52px;
  padding: 0 16px;
  margin-top: 28px;

  background: #fff;
  border: 1px solid #e8ecf3;
  border-radius: 12px;
}

.search-symbol {
  color: #8591a6;
  line-height: 1;
}

.search-bar input {
  flex: 1;
  width: 0;
  min-width: 0;

  color: #29364a;
  background: transparent;
  border: 0;
  outline: none;

  font-size: 12px;
}

.search-bar input::placeholder {
  color: #9ba5b4;
}

.search-hint {
  color: #a3adbc;
  font-size: 9px;
  letter-spacing: 1px;
}

/* =========================================================
   05. PDF 工具列表
   ========================================================= */

.tools-section {
  margin-top: 52px;
}

/* 工具区域标题 */

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;

  margin-bottom: 23px;
}

.section-heading h2 {
  margin: 0;

  color: #26354c;
  font-size: 17px;
  font-weight: 750;
}

.section-heading p {
  margin: 7px 0 0;

  color: #8b95a5;
  font-size: 11px;
}

.tool-count {
  flex: 0 0 auto;
  color: #7d899c;
  font-size: 11px;
}

/* 工具卡片网格 */

.tool-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 17px;
}

/* 单个工具卡片 */

.tool-card {
  display: flex;
  flex-direction: column;

  min-width: 0;
  min-height: 224px;
  padding: 22px 20px 0;

  color: inherit;
  background: #fff;
  border: 1px solid #e9edf4;
  border-radius: 14px;

  text-align: left;
  cursor: pointer;

  transition:
    border-color 0.18s,
    transform 0.18s,
    box-shadow 0.18s;
}

.tool-card:hover {
  transform: translateY(-2px);
  border-color: #d4ddfa;
  box-shadow: 0 9px 24px rgba(33, 54, 92, 0.055);
}

/* 工具图标 */

.tool-icon {
  display: grid;
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  place-items: center;

  margin-bottom: 21px;

  color: #3865e8;
  background: #edf2ff;
  border-radius: 12px;
}

.tool-icon.split {
  color: #0e9c86;
  background: #e9f8f4;
}

.tool-icon.compress {
  color: #b17a24;
  background: #fff5e6;
}

.tool-icon.permission {
  color: #7656c9;
  background: #f1edff;
}

.tool-icon.encryption {
  color: #d05c70;
  background: #fff0f3;
}

/* 工具名称和介绍 */

.tool-name {
  color: #253249;
  font-size: 14px;
  font-weight: 750;
}

.tool-description {
  margin-top: 8px;

  color: #8792a3;
  font-size: 11px;
  line-height: 1.7;
}

/* 卡片底部 */

.tool-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;

  padding: 15px 0;
  margin-top: auto;

  color: #61708a;
  border-top: 1px solid #f0f2f6;
  font-size: 10px;
}

.card-arrow {
  color: #4169e8;
  font-size: 16px;
}

/* 搜索无匹配结果 */

.empty-state {
  padding: 42px 15px;

  color: #8994a6;
  background: #fff;
  border: 1px dashed #e1e6ef;
  border-radius: 12px;

  text-align: center;
  font-size: 12px;
}

/* 页面底部 */

.page-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  padding-top: 18px;
  margin-top: auto;

  color: #9aa4b4;
  border-top: 1px solid #e8edf3;
  font-size: 10px;
}

/* =========================================================
   06. 通用弹窗
   ========================================================= */

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 24px;
  overflow-y: auto;

  background: rgba(32, 43, 63, 0.38);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
}

.modal {
  position: relative;

  display: flex;
  flex-direction: column;

  width: 100%;
  max-width: 500px;
  max-height: calc(100vh - 48px);
  min-height: 0;

  overflow: hidden;

  background: #fff;
  border: 1px solid rgba(230, 234, 242, 0.9);
  border-radius: 20px;

  box-shadow: 0 24px 80px rgba(20, 32, 54, 0.2);
}

/* 解密弹窗使用更宽的布局 */

.modal.unlock-modal {
  max-width: 560px;
}

/* 弹窗顶部 */

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  min-height: 58px;
  flex: 0 0 auto;
  padding: 0 24px;

  border-bottom: 1px solid #f0f2f6;
}

.modal-brand {
  display: flex;
  align-items: center;
  gap: 9px;

  color: #52617a;
  font-size: 12px;
  font-weight: 650;
}

.modal-brand-dot {
  width: 7px;
  height: 7px;
  background: #315ee7;
  border-radius: 50%;
}

/* 弹窗关闭按钮 */

.modal-close {
  display: grid;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  place-items: center;

  padding: 0;

  color: #8490a3;
  background: transparent;
  border: 0;
  border-radius: 8px;

  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.modal-close:hover:not(:disabled) {
  color: #26354c;
  background: #f3f5f9;
}

/* =========================================================
   07. 文件选择区域
   ========================================================= */

.unlock-content {
  display: flex;
  flex-direction: column;

  min-height: 0;
  padding: 24px;

  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

/* 功能标题 */

.unlock-title-row {
  display: flex;
  align-items: center;
  gap: 15px;

  margin-bottom: 27px;
}

.unlock-icon {
  display: grid;
  width: 58px;
  height: 58px;
  flex: 0 0 58px;
  place-items: center;

  color: #315ee7;
  background: #edf2ff;
  border-radius: 16px;
}

.unlock-title-copy {
  min-width: 0;
}

.unlock-title-copy h2 {
  margin: 0;

  color: #253249;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.unlock-title-copy p {
  margin: 8px 0 0;

  color: #8390a4;
  font-size: 12px;
  line-height: 1.7;
}

/* 功能步骤区域 */

.unlock-section {
  margin-bottom: 25px;
}

.section-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.step-number {
  display: grid;
  width: 27px;
  height: 27px;
  flex: 0 0 27px;
  place-items: center;

  color: #315ee7;
  background: #edf2ff;
  border-radius: 8px;

  font-size: 11px;
  font-weight: 750;
}

.section-title-row h3 {
  margin: 0;

  color: #29364a;
  font-size: 14px;
  font-weight: 750;
}

.section-description {
  margin: 8px 0 14px 37px;

  color: #8994a6;
  font-size: 11px;
  line-height: 1.7;
}

/* 空文件选择区域 */

.file-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  min-height: 126px;
  padding: 18px;

  background: #fafbfe;
  border: 1px dashed #dce3ef;
  border-radius: 12px;

  text-align: center;
  cursor: pointer;
}

.file-empty.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.empty-file-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;

  margin-bottom: 8px;

  color: #315ee7;
  background: #edf2ff;
  border-radius: 10px;
}

.empty-file-title {
  color: #53617a;
  font-size: 12px;
  font-weight: 650;
}

.empty-file-description {
  margin-top: 5px;

  color: #9aa4b4;
  font-size: 10px;
}

/* 已选择文件列表 */

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;

  max-height: 190px;
  padding: 2px;

  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 11px;

  min-width: 0;
  padding: 10px;

  background: #fafbfe;
  border: 1px solid #edf0f5;
  border-radius: 10px;
}

/* 文件类型图标 */

.file-type-icon {
  display: grid;
  width: 37px;
  height: 42px;
  flex: 0 0 37px;
  place-items: center;

  color: #d95454;
  background: #fff0f0;
  border-radius: 8px;

  font-size: 10px;
  font-weight: 800;
}

/* 文件名称和路径 */

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  overflow: hidden;

  color: #36445b;
  font-size: 12px;
  font-weight: 650;

  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-path {
  margin-top: 5px;
  overflow: hidden;

  color: #99a3b2;
  font-size: 10px;

  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 移除文件按钮 */

.remove-file {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  place-items: center;

  color: #8e99aa;
  background: transparent;
  border: 0;
  border-radius: 7px;

  font-size: 19px;
  cursor: pointer;
}

.remove-file:hover:not(:disabled) {
  color: #d95353;
  background: #fff0f0;
}

/* 文件操作按钮 */

.file-actions {
  display: flex;
  align-items: center;
  gap: 12px;

  margin-top: 12px;
}

/* =========================================================
   08. 按钮与输出目录
   ========================================================= */

/* 通用按钮 */

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  min-height: 40px;
  padding: 0 15px;

  border: 1px solid transparent;
  border-radius: 9px;

  font-size: 12px;
  font-weight: 650;
  cursor: pointer;

  transition:
    background 0.15s,
    border-color 0.15s,
    transform 0.15s;
}

.button:active:not(:disabled) {
  transform: translateY(1px);
}

/* 次要按钮 */

.button-secondary {
  color: #4f5f78;
  background: #fff;
  border-color: #e1e6ef;
}

.button-secondary:hover:not(:disabled) {
  background: #f8faff;
  border-color: #cfd8e8;
}

/* 主要按钮 */

.button-primary {
  color: #fff;
  background: #315ee7;
  border-color: #315ee7;
  box-shadow: 0 4px 10px rgba(49, 94, 231, 0.14);
}

.button-primary:hover:not(:disabled) {
  background: #244ed0;
  border-color: #244ed0;
}

/* 文字按钮 */

.text-button {
  padding: 7px 4px;

  color: #8792a3;
  background: transparent;
  border: 0;

  font-size: 11px;
  cursor: pointer;
}

.text-button:hover:not(:disabled) {
  color: #d95353;
}

/* 输出目录选择 */

.folder-picker {
  display: flex;
  align-items: center;
  gap: 12px;

  min-width: 0;
  padding: 13px;

  background: #fafbfe;
  border: 1px solid #edf0f5;
  border-radius: 12px;
}

.folder-icon {
  display: grid;
  width: 39px;
  height: 39px;
  flex: 0 0 39px;
  place-items: center;

  color: #bd8b2f;
  background: #fff5e4;
  border-radius: 10px;
}

.folder-info {
  flex: 1;
  min-width: 0;
}

.folder-label {
  margin-bottom: 5px;

  color: #66748a;
  font-size: 10px;
}

.folder-path {
  overflow: hidden;

  color: #36445b;
  font-size: 11px;

  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-button {
  min-height: 34px;
  padding: 0 12px;
}

/* =========================================================
   09. PDF 密码与权限设置
   ========================================================= */

.password-label {
  display: block;
  margin: 14px 0 7px;

  color: #253249;
  font-size: 13px;
  font-weight: 500;
}

/* 密码输入框 */

.unlock-section input[type="password"],
.password-mode-select {
  display: block;

  width: 100%;
  min-height: 40px;
  padding: 9px 12px;

  color: #253249;
  background: #fff;
  border: 1px solid #e1e6ef;
  border-radius: 9px;

  font-family: inherit;
  font-size: 13px;

  transition: border-color 0.15s ease;
}

.unlock-section input[type="password"]::placeholder {
  color: #8994a6;
}

.unlock-section input[type="password"]:focus,
.password-mode-select:focus {
  outline: none;
  border-color: #315ee7;
}

/* 密码权限模式选择框 */

.password-mode-wrapper {
  position: relative;
  width: 100%;
}

.password-mode-select {
  appearance: none;
  -webkit-appearance: none;

  padding-right: 40px;
  background-image: none;

  cursor: pointer;
}

.password-mode-select:disabled {
  cursor: not-allowed;
}

.password-mode-arrow {
  position: absolute;
  top: 50%;
  right: 15px;

  width: 8px;
  height: 8px;

  border-right: 1.5px solid #8490a3;
  border-bottom: 1.5px solid #8490a3;

  transform: translateY(-70%) rotate(45deg);
  pointer-events: none;
}

/* PDF 操作权限选项 */

.permission-options {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 20px;

  margin-top: 16px;
}

.permission-options label {
  display: inline-flex;
  align-items: center;
  gap: 7px;

  color: #53617a;
  font-size: 13px;
  cursor: pointer;
}

.permission-options input[type="checkbox"] {
  width: 15px;
  height: 15px;
  margin: 0;

  accent-color: #315ee7;
  cursor: pointer;
}

/* =========================================================
   10. 状态提示与处理结果
   ========================================================= */

/* 操作状态提示 */

.status-message {
  display: flex;
  align-items: flex-start;
  gap: 9px;

  padding: 11px 12px;
  margin-bottom: 14px;

  color: #53617a;
  background: #f5f7fc;
  border: 1px solid #e8edf6;
  border-radius: 10px;

  font-size: 11px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.status-message-icon {
  display: grid;
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  place-items: center;

  color: #315ee7;
  background: #e7edff;
  border-radius: 50%;

  font-size: 11px;
  font-weight: 800;
}

/* 处理结果面板 */

.result-panel {
  padding: 15px;
  margin-bottom: 16px;

  background: #fbfcff;
  border: 1px solid #e6ebf4;
  border-radius: 12px;
}

.result-heading {
  display: flex;
  align-items: center;
  gap: 9px;

  color: #33425a;
  font-size: 12px;
}

.result-check {
  display: grid;
  width: 23px;
  height: 23px;
  place-items: center;

  color: #17835c;
  background: #e4f7ef;
  border-radius: 50%;

  font-size: 12px;
  font-weight: 800;
}

/* 处理结果统计 */

.result-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;

  margin: 14px 0;
}

.result-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;

  padding: 11px 5px;

  background: #fff;
  border: 1px solid #edf0f5;
  border-radius: 9px;
}

.stat-value {
  color: #33425a;
  font-size: 19px;
  font-weight: 800;
}

.stat-label {
  color: #8b96a7;
  font-size: 10px;
}

/* 成功和失败状态 */

.success-text {
  color: #16845b;
}

.error-text {
  color: #d95353;
}

/* 单个文件处理结果 */

.result-list {
  display: flex;
  flex-direction: column;
  gap: 10px;

  max-height: 180px;
  overflow-y: auto;
}

.result-item {
  display: flex;
  align-items: flex-start;
  gap: 9px;

  min-width: 0;
}

.result-item-status {
  display: grid;
  width: 19px;
  height: 19px;
  flex: 0 0 19px;
  place-items: center;

  border-radius: 50%;
  font-size: 10px;
  font-weight: 800;
}

.result-ok {
  color: #16845b;
  background: #e4f7ef;
}

.result-failed {
  color: #c74747;
  background: #fff0f0;
}

.result-item-info {
  flex: 1;
  min-width: 0;
}

.result-item-name {
  overflow: hidden;

  color: #48566e;
  font-size: 11px;
  font-weight: 650;

  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-item-message {
  margin-top: 4px;

  color: #929daf;
  font-size: 10px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

/* 功能说明 */

.unlock-note {
  display: flex;
  align-items: flex-start;
  gap: 9px;

  padding: 11px 12px;

  color: #8390a3;
  background: #f7f8fc;
  border-radius: 9px;

  font-size: 10px;
  line-height: 1.8;
}

/* 弹窗底部操作区 */

.unlock-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;

  padding-top: 19px;
  margin-top: 20px;

  border-top: 1px solid #edf0f5;
}

.cancel-button {
  min-width: 78px;
}

.unlock-footer .button-primary {
  min-width: 126px;
}

/* =========================================================
   11. 通用表单控件
   ========================================================= */

/* 输入框 */

input[type="text"],
input[type="number"],
input[type="password"],
input[type="search"] {
  box-sizing: border-box;

  width: 100%;
  min-height: 38px;
  padding: 0 12px;

  border: 1px solid #dcdfe6;
  border-radius: 8px;
  outline: none;

  background: #fff;
  color: #303133;

  font-size: 13px;

  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

/* 下拉框 */

select {
  box-sizing: border-box;

  min-height: 38px;
  padding: 0 32px 0 12px;

  border: 1px solid #dcdfe6;
  border-radius: 8px;
  outline: none;

  background-color: #fff;
  color: #303133;

  font-size: 13px;
  cursor: pointer;

  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

/* 文本域 */

textarea {
  box-sizing: border-box;

  width: 100%;
  min-height: 80px;
  padding: 10px 12px;

  border: 1px solid #dcdfe6;
  border-radius: 8px;
  outline: none;

  background: #fff;
  color: #303133;

  font-size: 13px;
  line-height: 1.6;
  resize: vertical;

  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

/* 聚焦状态 */

input:focus,
select:focus,
textarea:focus {
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.12);
}

/* 禁用状态 */

input:disabled,
select:disabled,
textarea:disabled {
  background: #f5f7fa;
  color: #a8abb2;
  cursor: not-allowed;
}

/* 占位文字 */

input::placeholder,
textarea::placeholder {
  color: #a8abb2;
}

/* 文件选择按钮 */

input[type="file"] {
  font-size: 12px;
}

/* 数字输入框 */

input[type="number"] {
  font-variant-numeric: tabular-nums;
}

/* 字体预览 */

.font-preview {
  padding: 14px;
  margin-top: 12px;

  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;

  background: var(--card-background, #f9fafb);
}

.font-preview-label {
  margin-bottom: 12px;

  color: #888;
  font-size: 12px;
}

.font-preview-content {
  display: flex;
  align-items: center;
  justify-content: center;

  min-height: 48px;

  color: #333;
  font-size: 24px;
  text-align: center;
  overflow-wrap: anywhere;
}

.font-preview-name {
  margin-top: 10px;

  color: #888;
  font-size: 12px;
  text-align: right;
}

/* =========================================================
   12. 加载动画
   ========================================================= */

.loading-spinner {
  width: 13px;
  height: 13px;

  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;

  animation: spin 0.7s linear infinite;
}

.spinner {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* =========================================================
   13. 捐赠弹窗
   ========================================================= */

.donation-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 20px;

  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);

  cursor: pointer;
}

/* 捐赠卡片 */

.donation-card {
  position: relative;

  width: 420px;
  max-width: 100%;
  padding: 28px 24px 24px;

  border-radius: 16px;

  background: var(--el-bg-color, #fff);
  color: var(--el-text-color-primary, #303133);

  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
  text-align: center;
}

/* 关闭按钮 */

.donation-close {
  position: absolute;
  top: 12px;
  right: 12px;

  display: grid;
  place-items: center;

  width: 30px;
  height: 30px;

  border: none;
  border-radius: 8px;

  background: transparent;
  color: var(--el-text-color-secondary, #909399);

  cursor: pointer;
}

/* 捐赠图标 */

.donation-icon {
  display: grid;
  place-items: center;

  width: 56px;
  height: 56px;
  margin: 0 auto 14px;

  border-radius: 16px;

  background: #fff3dc;
  color: #d97706;
}

/* 捐赠标题和说明 */

.donation-card h3 {
  margin: 0 0 10px;
  font-size: 19px;
}

.donation-card p {
  margin: 0 0 20px;

  color: var(--el-text-color-secondary, #909399);
  font-size: 13px;
  line-height: 1.7;
}

/* 收款信息占位区域 */

.donation-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;

  padding: 24px 12px;

  border: 1px dashed var(--el-border-color, #dcdfe6);
  border-radius: 12px;

  color: var(--el-text-color-secondary, #909399);
}

.donation-placeholder span {
  color: var(--el-text-color-primary, #303133);
}

.donation-placeholder small {
  font-size: 12px;
}

/* 收款二维码 */

.donation-qr {
  display: block;

  width: 220px;
  max-width: 100%;
  height: auto;

  margin: 12px auto 0;

  object-fit: contain;
  border-radius: 8px;
}

/* 捐赠确认按钮 */

.donation-confirm {
  width: 100%;
  padding: 10px;
  margin-top: 20px;

  border: none;
  border-radius: 8px;

  background: var(--el-color-primary, #409eff);
  color: #fff;

  cursor: pointer;
}

/* =========================================================
   14. 关于我们弹窗
   ========================================================= */

.about-mask {
  position: fixed;
  inset: 0;
  z-index: 100000;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 20px;

  background: rgba(15, 23, 42, 0.48);
  backdrop-filter: blur(5px);
}

/* 弹窗主体 */

.about-card {
  position: relative;

  display: flex;
  flex-direction: column;

  width: 460px;
  max-width: 100%;
  max-height: 85vh;

  overflow: hidden;

  border: 1px solid #e5e7eb;
  border-radius: 18px;

  background: #fff;
  color: #303133;

  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.22);
}

/* 关闭按钮 */

.about-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 1;

  display: grid;
  place-items: center;

  width: 32px;
  height: 32px;

  border: none;
  border-radius: 8px;

  background: transparent;
  color: #909399;

  cursor: pointer;

  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.about-close:hover {
  background: #f2f3f5;
  color: #303133;
}

/* 顶部项目信息 */

.about-header {
  flex-shrink: 0;

  padding: 30px 24px 22px;

  background: linear-gradient(180deg, #f4f8ff 0%, #fff 100%);
  text-align: center;
}

.about-logo {
  display: grid;
  place-items: center;

  width: 62px;
  height: 62px;
  margin: 0 auto 14px;

  border-radius: 17px;

  background: #e8f1ff;
  color: #3478db;
}

.about-header h3 {
  margin: 0;

  font-size: 21px;
  font-weight: 650;
  letter-spacing: 0.3px;
}

.about-subtitle {
  margin: 9px 0 12px;

  color: #909399;
  font-size: 12px;
}

.about-version {
  display: inline-flex;
  align-items: center;

  padding: 5px 10px;

  border: 1px solid #dce8ff;
  border-radius: 20px;

  background: #edf4ff;
  color: #3478db;

  font-size: 12px;
}

/* 更新检查区域 */

.about-update {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;

  margin-top: 12px;

  color: var(--text-secondary, #888);
  font-size: 12px;
}

.about-update label {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}

.about-update button {
  display: flex;
  align-items: center;
  gap: 4px;

  padding: 5px 10px;

  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;

  background: transparent;
  color: inherit;

  cursor: pointer;
}

.about-update button:hover {
  color: var(--primary-color, #409eff);
  border-color: var(--primary-color, #409eff);
}

/* 内容滚动区域 */

.about-content {
  min-height: 0;
  padding: 0 24px;

  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
}

/* 内容分区 */

.about-section {
  padding: 17px 0;
  border-top: 1px solid #f0f1f3;
}

.about-section h4 {
  display: flex;
  align-items: center;
  gap: 8px;

  margin: 0 0 13px;

  color: #303133;
  font-size: 13px;
  font-weight: 600;
}

/* 项目仓库入口 */

.about-links {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.about-link {
  display: flex;
  align-items: center;
  gap: 8px;

  min-width: 0;
  padding: 11px 12px;

  border: 1px solid #e5e7eb;
  border-radius: 10px;

  background: #fff;
  color: #303133;

  font-size: 13px;
  cursor: pointer;

  transition:
    background 0.15s,
    border-color 0.15s;
}

.about-link span {
  flex: 1;
  text-align: left;
}

.about-link:hover:not(:disabled) {
  border-color: #b8d0fa;
  background: #f5f8ff;
}

.about-link:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* 项目参与人员 */

.about-members {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.about-member {
  display: flex;
  align-items: center;
  gap: 10px;

  font-size: 12px;
}

.member-avatar {
  display: grid;
  place-items: center;

  flex-shrink: 0;
  width: 32px;
  height: 32px;

  border-radius: 50%;

  background: #f1f5f9;
  color: #64748b;
}

.member-name {
  flex: 1;
  color: #303133;
}

.member-role {
  padding: 4px 8px;

  border-radius: 6px;

  background: #f4f5f7;
  color: #7b8494;

  font-size: 11px;
}

/* 技术栈标签 */

.about-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.about-tags span {
  padding: 6px 10px;

  border: 1px solid #e5e7eb;
  border-radius: 7px;

  background: #fafafa;
  color: #606266;

  font-size: 11px;
}

/* 技术实现说明 */

.about-tech-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.about-tech-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  font-size: 12px;
}

.about-tech-name {
  flex-shrink: 0;
  color: #909399;
}

.about-tech-desc {
  color: #303133;
  text-align: right;
  overflow-wrap: anywhere;
}

/* 开源项目致谢 */

.about-thanks-text {
  margin: 0 0 14px;

  color: #7b8494;
  font-size: 12px;
  line-height: 1.8;
}

.about-opensource-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.about-opensource-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  padding: 11px 12px;

  border: 1px solid #edf0f4;
  border-radius: 10px;

  background: #fcfcfd;
}

.about-opensource-info {
  display: flex;
  flex-direction: column;
  gap: 5px;

  min-width: 0;
}

.about-opensource-name {
  color: #303133;
  font-size: 12px;
  font-weight: 600;
}

.about-opensource-desc {
  color: #909399;
  font-size: 11px;
}

/* 开源项目仓库链接 */

.about-repo-link {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  gap: 4px;

  padding: 6px 8px;

  border: none;
  border-radius: 6px;

  background: #edf4ff;
  color: #3478db;

  font-size: 11px;
  cursor: pointer;

  transition: background 0.15s ease;
}

.about-repo-link:hover {
  background: #dceaff;
}

/* 提示和项目说明 */

.about-hint {
  margin: 10px 0 0;

  color: #a0a4ad;
  font-size: 11px;
  line-height: 1.7;
}

.about-description p {
  margin: 0 0 8px;

  color: #7b8494;
  font-size: 12px;
  line-height: 1.8;
}

.about-description p:last-child {
  margin-bottom: 0;
}

/* 弹窗底部 */

.about-footer {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  padding: 15px 24px;

  border-top: 1px solid #f0f1f3;
  background: #fcfcfd;
}

.about-footer span {
  color: #a0a4ad;
  font-size: 11px;
}

.about-footer button {
  padding: 8px 18px;

  border: none;
  border-radius: 8px;

  background: #3478db;
  color: #fff;

  font-size: 12px;
  cursor: pointer;

  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.about-footer button:hover {
  background: #2868c7;
}

/* =========================================================
   15. 需求与建议弹窗
   ========================================================= */

.feedback-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 20px;

  background: rgba(0, 0, 0, 0.42);
  backdrop-filter: blur(3px);
}

.feedback-dialog {
  width: 100%;
  max-width: 380px;
  padding: 24px;

  border-radius: 16px;

  background: var(--dialog-bg, #fff);
  color: var(--text-color, #222);

  box-shadow: 0 16px 50px rgba(0, 0, 0, 0.16);
}

.feedback-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;

  margin-bottom: 24px;
}

.feedback-header h3 {
  margin: 0;

  font-size: 18px;
  font-weight: 600;
}

.feedback-header p {
  margin: 8px 0 0;

  color: #888;
  font-size: 13px;
}

.feedback-close {
  border: none;
  background: transparent;

  color: #999;
  font-size: 25px;
  cursor: pointer;
}

/* 反馈入口列表 */

.feedback-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feedback-option {
  display: flex;
  align-items: center;

  width: 100%;
  padding: 15px;

  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;

  background: transparent;
  color: inherit;

  text-align: left;
  cursor: pointer;

  transition:
    background 0.2s,
    border-color 0.2s;
}

.feedback-option:hover {
  border-color: #999;
  background: rgba(128, 128, 128, 0.06);
}

.feedback-icon {
  display: flex;
  align-items: center;
  justify-content: center;

  width: 42px;
  height: 42px;

  border-radius: 10px;

  color: #fff;
  font-size: 17px;
  font-weight: 700;
}

.gitee-icon {
  background: #c71d23;
}

.github-icon {
  background: #24292f;
  font-size: 13px;
}

.feedback-info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;

  margin-left: 13px;
}

.feedback-name {
  font-size: 14px;
  font-weight: 600;
}

.feedback-desc {
  color: #999;
  font-size: 12px;
}

.feedback-arrow {
  color: #999;
  font-size: 25px;
}

.feedback-footer {
  margin-top: 22px;

  color: #999;
  font-size: 12px;
  text-align: center;
}

/* 反馈弹窗过渡 */

.feedback-dialog-enter-active,
.feedback-dialog-leave-active {
  transition: opacity 0.2s;
}

.feedback-dialog-enter-active .feedback-dialog,
.feedback-dialog-leave-active .feedback-dialog {
  transition: transform 0.2s;
}

.feedback-dialog-enter-from,
.feedback-dialog-leave-to {
  opacity: 0;
}

.feedback-dialog-enter-from .feedback-dialog,
.feedback-dialog-leave-to .feedback-dialog {
  transform: translateY(10px) scale(0.98);
}

/* =========================================================
   16. 软件更新弹窗
   ========================================================= */

.update-mask {
  position: fixed !important;
  inset: 0;
  z-index: 999999 !important;
}

.update-info {
  width: 100%;
  padding: 12px;
  margin: 16px 0;

  border-radius: 8px;

  background: var(--el-fill-color-light, #f5f5f5);
  text-align: left;
}

.update-version {
  display: flex;
  justify-content: space-between;

  margin-bottom: 10px;

  font-size: 13px;
}

.update-version:last-child {
  margin-bottom: 0;
}

.update-notes {
  padding-top: 12px;
  margin-top: 14px;

  border-top: 1px solid var(--el-border-color, #ddd);
}

.update-notes strong {
  font-size: 13px;
}

.update-notes p {
  font-size: 12px;
  line-height: 1.7;
  text-align: left;
  white-space: pre-wrap;
}

/* 更新进度 */

.update-progress {
  width: 100%;
  margin: 20px 0;
}

.progress-track {
  height: 7px;
  overflow: hidden;

  border-radius: 10px;
  background: var(--el-fill-color, #eee);
}

.progress-value {
  height: 100%;

  border-radius: 10px;

  background: var(--el-color-primary, #409eff);

  transition: width 0.2s;
}

.update-progress small {
  display: block;
  margin-top: 8px;

  color: var(--el-text-color-secondary, #999);
  text-align: right;
}

/* =========================================================
   17. 动画
   ========================================================= */

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* =========================================================
   18. 响应式布局
   ========================================================= */

/* 中等屏幕：缩小侧边栏，工具卡片改为两列 */

@media (max-width: 1100px) {
  .sidebar {
    width: 210px;
    padding-right: 14px;
    padding-left: 14px;
  }

  .main-content {
    width: calc(100% - 210px);
    padding-right: 28px;
    padding-left: 28px;
    margin-left: 210px;
  }

  .tool-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* 窄屏幕：侧边栏收缩为图标导航 */

@media (max-width: 700px) {
  .sidebar {
    position: static;

    width: 70px;
    flex: 0 0 70px;
    padding: 20px 8px 12px;
  }

  .brand {
    justify-content: center;
    padding: 0 0 28px;
  }

  .brand-copy,
  .nav-caption,
  .nav-item > span:not(.nav-icon) {
    display: none;
  }

  .nav-item {
    justify-content: center;
    min-height: 44px;
    padding: 0;
  }

  .nav-icon {
    flex-basis: auto;
  }

  .sidebar-footer {
    padding-right: 0;
    padding-left: 0;
  }

  .footer-list {
    align-items: center;
  }

  .footer-item span {
    display: none;
  }

  /* 主内容区域 */

  .main-content {
    width: calc(100% - 70px);
    padding: 28px 16px 16px;
    margin-left: 0;
  }

  .page-header-title-row h1 {
    font-size: 26px;
  }

  .tools-section {
    margin-top: 32px;
  }

  .tool-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .tool-card {
    min-height: 195px;
  }

  .search-hint {
    display: none;
  }

  /* 通用弹窗 */

  .modal-backdrop {
    align-items: center;
    padding: 12px;
    box-sizing: border-box;
  }

  .modal {
    max-height: calc(100vh - 50px);
    border-radius: 16px;
  }

  .unlock-content {
    padding: 18px;
  }

  .unlock-title-copy h2 {
    font-size: 18px;
  }

  .unlock-section {
    margin-bottom: 21px;
  }

  .modal-header {
    padding-right: 16px;
    padding-left: 18px;
  }

  /* 关于我们弹窗 */

  .about-mask {
    padding: 12px;
  }

  .about-card {
    max-height: 90vh;
  }

  .about-header {
    padding-top: 26px;
  }

  .about-content {
    padding: 0 18px;
  }

  .about-footer {
    padding: 14px 18px;
  }
}

/* 超小屏幕：进一步压缩布局 */

@media (max-width: 420px) {
  .sidebar {
    width: 56px;
    flex-basis: 56px;
    padding-right: 5px;
    padding-left: 5px;
  }

  .main-content {
    width: calc(100% - 56px);
    padding-right: 12px;
    padding-left: 12px;
  }

  /* 解密弹窗 */

  .unlock-content {
    padding: 15px;
  }

  .unlock-title-row {
    align-items: flex-start;
    gap: 11px;
  }

  .unlock-icon {
    width: 46px;
    height: 46px;
    flex-basis: 46px;
    border-radius: 12px;
  }

  .unlock-title-copy h2 {
    font-size: 16px;
  }

  .section-description {
    margin-left: 0;
  }

  .file-actions {
    flex-wrap: wrap;
  }

  .folder-picker {
    gap: 8px;
    padding: 9px;
  }

  .folder-icon {
    width: 32px;
    height: 32px;
    flex-basis: 32px;
  }

  .folder-button {
    padding: 0 9px;
  }

  .permission-options {
    gap: 12px;
  }
}

/* 屏幕高度较小时：调整弹窗位置和内部间距 */

@media (max-height: 650px) {
  .modal-backdrop {
    align-items: flex-start;
  }

  .modal {
    max-height: calc(100vh - 50px);
  }

  .unlock-content {
    padding-top: 16px;
    padding-bottom: 16px;
  }

  .unlock-title-row {
    margin-bottom: 18px;
  }

  .unlock-section {
    margin-bottom: 17px;
  }

  .unlock-footer {
    padding-top: 13px;
    margin-top: 14px;
  }
}
</style>