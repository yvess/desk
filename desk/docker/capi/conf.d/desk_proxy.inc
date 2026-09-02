proxy_set_header  Host $host;
proxy_set_header  X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_buffering   off;
proxy_redirect    off;
proxy_read_timeout 60;
proxy_pass        http://cdb;
