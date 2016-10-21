window.onload = function() {
	$('#create-user').submit(function() {
		var message = ""
		if ($('#first-name').val() === "") {
			message = "First Name cannot be empty !"
		} else if ($('#email').val() ===  "") {
			message = "Email Id cannot be empty !"
		} else if ($('#password').val() === "") {
			message = "Password cannot be empty !"
		} else if ($('#password').val().length < 6) {
			message = "Password cannot be less than 6 characters"
		} else if ($('#password').val() != $('#password-again').val()) {
			message = "Passwords do not match !"
		} else {
			return true
		}
		$('#error-message').html(message)
		return false
	})
}