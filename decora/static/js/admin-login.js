window.onload = function() {
	main()
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function main() {
	$('#login-button').click(function() {
		var email = $('#email').val();
		var password = $('#password').val();
		var csrftoken = Cookies.get('csrftoken');
		
		if (email === "") {
			$('#error-message').html("Email Id cannot be blank !");
		}
		else if (password === "") {
			$('#error-message').html("Password cannot be blank !");
		}
		else {

			$.ajaxSetup({
			    beforeSend: function(xhr, settings) {
			        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
			            xhr.setRequestHeader("X-CSRFToken", csrftoken);
			        }
			    }
			});


			$.ajax({
				type: "POST",
				url: "/admin/login",
				data: {
					email: email,
					password: password
				},
				success: function(data) {
					console.log(data);
					if (data['status'] === 0) {
						$('#error-message').html(data['message']);
					} else {
						window.location.href = "/admin"
					}
				}
			});
		}
	})
}