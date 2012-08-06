function (doc, req)
{
  if (doc.type == "queue" && doc.state == "created") {
    return true;
  }

  return false;
}