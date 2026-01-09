-- OSC52 clipboard support for Neovim < 0.10 over SSH
return {
    'ojroques/nvim-osc52',
    cond = function()
        -- Only load if over SSH and neovim < 0.10
        return os.getenv("SSH_TTY") ~= nil and vim.fn.has('nvim-0.10') == 0
    end,
    config = function()
        require('osc52').setup({
            max_length = 0,      -- Maximum length of selection (0 for unlimited)
            silent = false,      -- Disable message on successful copy
            trim = false,        -- Trim surrounding whitespaces
        })

        -- Set as clipboard provider
        local function copy(lines, _)
            require('osc52').copy(table.concat(lines, '\n'))
        end

        local function paste()
            return { vim.fn.split(vim.fn.getreg(''), '\n'), vim.fn.getregtype('') }
        end

        vim.g.clipboard = {
            name = 'osc52',
            copy = { ['+'] = copy, ['*'] = copy },
            paste = { ['+'] = paste, ['*'] = paste },
        }
    end,
}
