function (doc, req)
{
  if (doc.type == "queue" && doc.state == "new") {
    return true;
  }

  return false;
}