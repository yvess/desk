function(doc, req)
{
  if(doc.type == "queue") {
    return true;
  }

  return false;
}