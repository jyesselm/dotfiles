return {
    'gennaro-tedesco/nvim-jqx',
    ft = { 'json', 'yaml' },
    keys = {
        { '<leader>jq', ':JqxList<CR>', desc = 'Browse JSON keys' },
        { '<leader>jQ', ':JqxQuery<CR>', desc = 'Run jq query' },
    },
}
