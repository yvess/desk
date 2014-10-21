# do nothing on default
default:

# PIP

# save current requirements
freeze:
	pip freeze -r /tmp/requirements.txt > /tmp/requirements.txt
	sed -i "s/-e git+https:\/\/github.com\/yvess\/desk.git/\#-e git+https:\/\/github.com\/yvess\/desk.git/" /tmp/requirements.txt
	egrep "##|lxml" /tmp/requirements.txt > /tmp/requirements_new.txt
	egrep "##|lxml" /tmp/requirements.txt -v >> /tmp/requirements_new.txt
	rm /tmp/requirements.txt && mv /tmp/requirements_new.txt /tmp/requirements.txt
	cp /tmp/requirements.txt images/dns/requirements.txt
	cp /tmp/requirements.txt images/master/requirements.txt
