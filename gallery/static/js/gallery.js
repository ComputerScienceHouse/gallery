function afterMkdir(data) {
    console.log(data);
    console.log(data['success']);
    if (data['success'].length > 0) {
        $('#descriptions .modal-body').append("<div class='form-group'>");
        for (var i = 0, len = data['success'].length; i < len; i++) {
            var dir_name = data['success'][i]['id'];
            var dir_id = data['success'][i]['name'];
            console.log("Dir: " + dir_name + " (" + dir_id + ")");
            var field = "<label class='control-label' for='desc-" + dir_id + "'>Description for folder '<strong>" + dir_name + "</strong>'</label>"
                        + "<input type='text' class='form-control' id='desc-" + dir_id + "'>";
            $('#descriptions .modal-body').append(field);
        }
        $('#descriptions input').focusout(function() {
            $.ajax({
                type: "POST",
                url: "/api/dir/describe/" + dir_id,
                data: {
                    description: $('input[id="desc-' + dir_id + '"]').val()
                },
                success: function() {
                    console.log("Successfully posted description for " + dir_name);
                }
            });
        });
        $('#descriptions .modal-body').append("</div>");
        $('descriptions').modal('show');
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
