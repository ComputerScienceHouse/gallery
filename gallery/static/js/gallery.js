function afterMkdir(data) {
    console.log(data);
    // TODO pop up a thing to create a directory description for each
    // new dir
    // /api/dir/describe/<id>
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
