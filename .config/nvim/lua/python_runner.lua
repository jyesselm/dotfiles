local M = {}
local output_buf, output_win, job

function M.run()
    if vim.bo.filetype ~= "python" then
        vim.notify("Open a Python file to run it", vim.log.levels.WARN)
        return
    end
    local file = vim.api.nvim_buf_get_name(0)
    if file == "" then
        vim.notify("Save your Python file with a name first", vim.log.levels.WARN)
        return
    end
    if job and vim.fn.jobwait({ job }, 0)[1] == -1 then
        vim.notify("Python is still running", vim.log.levels.WARN)
        return
    end
    vim.cmd("write")
    local editor = vim.api.nvim_get_current_win()
    local inserting = vim.api.nvim_get_mode().mode:sub(1, 1) == "i"
    local previous_buf = output_buf
    output_buf = vim.api.nvim_create_buf(false, true)
    if output_win and vim.api.nvim_win_is_valid(output_win) then
        vim.api.nvim_win_set_buf(output_win, output_buf)
        vim.api.nvim_set_current_win(output_win)
    else
        vim.cmd("botright 12split")
        output_win = vim.api.nvim_get_current_win()
        vim.api.nvim_win_set_buf(output_win, output_buf)
    end
    if previous_buf and vim.api.nvim_buf_is_valid(previous_buf) then
        vim.api.nvim_buf_delete(previous_buf, { force = true })
    end
    vim.bo[output_buf].bufhidden = "hide"
    local python = "python3"
    if vim.env.VIRTUAL_ENV then
        local candidate = vim.env.VIRTUAL_ENV .. "/bin/python"
        if vim.fn.executable(candidate) == 1 then python = candidate end
    end
    -- List arguments preserve filenames containing spaces or shell characters.
    if vim.fn.has("nvim-0.11") == 1 then
        job = vim.fn.jobstart({ python, "-u", file }, { term = true })
    else
        job = vim.fn.termopen({ python, "-u", file })
    end
    vim.wo[output_win].number = false
    vim.wo[output_win].relativenumber = false
    vim.api.nvim_set_current_win(editor)
    if inserting then vim.cmd("startinsert") end
end

return M
