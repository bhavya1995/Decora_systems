window.onload = function() {
	$('.edit').click(function() {
		var element = $(this)
		var objectId = element.attr("id")
		window.location.href = "/admin/create-object?objectId=" + objectId
	})

	$('.delete').click(function() {
		var element = $(this)
		var objectId = element.attr("id")
		window.location.href = "/admin/delete-object?objectId=" + objectId
	})
}