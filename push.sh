
<pre>Process 75 stopped
* thread #1: tid = 75, 0x00007f54bc44df10, name = 'fhost'
    frame #0:
Process 75 stopped
* thread #8: tid = 75, 0x00007f558a7b7490 fhost`get(path='/HJvs.sh') + 27 at fhost.c:139, name = 'fhost/responder', stop reason = invalid address (fault address: 0x30)
    frame #0: {3:#018x} fhost`get(path='/HJvs.sh') + 27 at fhost.c:139
   136   get(SrvContext *ctx, const char *path)
   137   {
   138       StoredObj *obj = ctx->store->query(shurl_debase(path));
-> 139       switch (obj->type) {
   140           case ObjTypeFile:
   141               ctx->serve_file_id(obj->id);
   142               break;
(lldb) q</pre>