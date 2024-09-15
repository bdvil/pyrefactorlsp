# Python LSP for Refactoring

> [!WARNING]
> This is still highly experimental and it does not fully works yet.


## Test the project and contributing

Once the project installed, you can start the LSP with:
```prlsp serve```

In the LSP client, make a rcp connection to "127.0.0.1:8989".

If you use neovim, you can add in your config these helper functions:

```lua
local client_id = nil
local n_clients = 0
local attached_clients = {}


EnablePyrefactorLSP = function()
    if client_id == nil then
        client_id = vim.lsp.start({
            name = "pyrefactorlsp",
            cmd = vim.lsp.rpc.connect("127.0.0.1", 8989),
            root_dir = vim.fs.dirname(vim.fs.find({ "pyproject.toml", "setup.py" }, { upward = true })[1]),
        })
    end
    local buf = vim.api.nvim_get_current_buf()
    vim.lsp.buf_attach_client(buf, client_id)
    table.insert(attached_clients, buf)
    n_clients = n_clients + 1
end

DisablePyrefactorLSP = function()
    if client_id then
        local buf = vim.api.nvim_get_current_buf()
        vim.lsp.buf_detach_client(buf, client_id)
        for k, v in ipairs(attached_clients) do
            if v == buf then
                table.remove(attached_clients, k)
                n_clients = n_clients - 1
                break
            end
        end
    end
    if n_clients == 0 then
        vim.lsp.stop_client(client_id)
        client_id = nil
        attached_clients = {}
    end
end

StopPyrefactorLSP = function()
    if client_id then
        for _, buf in ipairs(attached_clients) do
            vim.lsp.buf_detach_client(buf, client_id)
        end
        vim.lsp.stop_client(client_id)
        client_id = nil
        n_clients = 0
        attached_clients = {}
    end
end

vim.cmd([[
  command! -range PyreEnable  execute 'lua EnablePyrefactorLSP()'
]])
vim.cmd([[
  command! -range PyreDisable  execute 'lua DisablePyrefactorLSP()'
]])
vim.cmd([[
  command! -range PyreStop  execute 'lua StopPyrefactorLSP()'
]])
```


You can then start the LSP with `:PyreEnable`.
