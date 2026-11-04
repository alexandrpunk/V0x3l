return {
  "sainnhe/sonokai",
  lazy = false,
  priority = 1000,
  config = function()
    vim.g.sonokai_style = "default"
    vim.g.sonokai_better_performance = 1
    vim.g.sonokai_disable_italic_comment = 1
    vim.g.sonokai_transparent_background = 0
    vim.g.sonokai_dim_inactive_windows = 0
    vim.cmd.colorscheme("sonokai")
  end,
}
