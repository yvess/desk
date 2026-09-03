rewrite ^ /desk_drawer/_changes?feed=$desk_feed&filter=desk_drawer/${desk_feed_doc}_${desk_feed_state}&include_docs=true&since=now? break;
include conf.d/desk_proxy.inc;
# an SSE feed is meant to stay open; the server-wide 60s would drop it and make
# the browser's EventSource reconnect every minute
proxy_read_timeout 3600;
