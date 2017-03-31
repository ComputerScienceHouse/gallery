function afterMkdir(data) {
    if (data['success'].length > 0) {
        for (var i = 0, len = data['success'].length; i < len; i++) {
            var dir_name = data['success'][i]['name'];
            var dir_id = data['success'][i]['id'];
            var field = "<label class='control-label' for='desc-" + dir_id + "'>"
                        + "Enter a description for folder \"<strong>" + dir_name + "</strong>\":"
                        + "<a href='/view/dir/" + dir_id + "'>(View folder)</a></label>"
                        + "<input type='text' class='form-control' id='desc-" + dir_id + "'>";
            $('#descriptions .modal-body .form-group').append(field);
        }
        $('#descriptions input').focusout(function() {
            $.ajax({
                type: "POST",
                url: "/api/dir/describe/" + dir_id,
                data: {
                    description: $('input[id="desc-' + dir_id + '"]').val()
                }
            });
        });
        $('#descriptions').modal('show');
    }
}

// Create a new directory
function createDirectory() {
    $.ajax({
        type: "POST",
        url: "/api/mkdir",
        data: {
            dir_name: $('input[name="gallery_dir_name"]').val(),
            parent_id: $('input[name="gallery_dir_id"]').val()
        },
        success: afterMkdir
    });
}

function afterUpload(file, response) {
    console.log("Uploaded file:");
    console.log(file);
    console.log("Response:");
    console.log(response);
    // TODO pop up a thing to create a directory description for each
    // /api/file/describe/<id>
}

// Rebuild the directory tree
function populateDirTree() {
    $.get("/api/get_dir_tree", function(data) {
        $('#fileList').tree({
            data: [data],
            autoOpen: 0
        });
        $('#fileList').bind(
            'tree.click',
            function(event) {
                // The clicked node is 'event.node'
                var node = event.node;
                $('input[name="gallery_dir_id"]').val(node.id);
            }
        );
    });
}
