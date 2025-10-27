$(document).ready(function () {
    
    function initSelect2($el) {
        $el.select2({
            placeholder: "Search product...",
            ajax: {
                url: "/product/search",
                dataType: 'json',
                delay: 250,
                data: function (params) {
                    return { q: params.term };
                },
                processResults: function (data) {
                    return {
                        results: data.map(function (prod) {
                            return { id: prod.id, text: prod.name };
                        }),
                    };
                },
                cache: true,
            },
            width: '100%',
        });
    }

    initSelect2($('.product-select'));

    $('#add_pr_line').on('click', function () {
        const newRow = `
            <tr>
                <td>
                    <select name="product_id[]" class="form-select product-select" required="required" style="width: 100%;"></select>
                </td>
                <td>
                    <input type="number" name="product_qty[]" class="form-control" min="1" value="1" required="required"/>
                </td>
                <td>
                    <input type="number" name="price_unit[]" class="form-control" min="0" step="0.01" required="required"/>
                </td>
                <td class="text-center">
                    <button type="button" class="btn btn-sm btn-danger remove-line">
                        <i class="fa fa-trash"></i>
                    </button>
                </td>
            </tr>`;
        $('#pr_lines_body').append(newRow);

        initSelect2($('#pr_lines_body tr:last .product-select'));
    });

    $(document).on('click', '.remove-line', function () {
        $(this).closest('tr').remove();
    });
});
