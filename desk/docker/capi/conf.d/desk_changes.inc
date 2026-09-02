rewrite ^ /desk_drawer/_changes?feed=$desk_feed&filter=desk_drawer/${desk_feed_doc}_${desk_feed_state}&include_docs=true&since=now? break;
include conf.d/desk_proxy.inc;
