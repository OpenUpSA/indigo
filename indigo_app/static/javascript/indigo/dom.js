$(function() {
  if (!Indigo.dom) Indigo.dom = {};

  // Selector for elements that are foreign to AKN documents, such as table editor buttons
  // and annotations.
  Indigo.dom.foreignElementsSelector = '.ig';

  /**
   * Removes foreign elements from the tree at root, executes callback,
   * and then replaces the foreign elements.
   *
   * This is useful for annotations because we inject foreign (ie. non-Akoma Ntoso)
   * elements into the rendered AKN document, such as table editor buttons, annotations
   * and issue indicators.
   *
   * @returns the result of callback()
   */
  Indigo.dom.withoutForeignElements = function(root, callback, selector) {
    var result,
      removed = [];

    selector = selector || Indigo.dom.foreignElementsSelector;

    // remove the foreign elements
    root.querySelectorAll(selector).forEach(function(elem) {
      var info = {e: elem};

      // store where the element was in the tree
      if (elem.nextSibling) info.before = elem.nextSibling;
      // no next sibling, it's the last child
      else info.parent = elem.parentElement;

      elem.parentElement.removeChild(elem);
      removed.push(info);
    });

    result = callback();

    // put the elements back
    removed.forEach(function(info) {
      if (info.before) info.before.parentElement.insertBefore(info.e, info.before);
      else info.parent.appendChild(info.e);
    });

    return result;
  }

  /**
   * Given a browser Range object, transform it into a target description
   * suitable for use with annotations. Will not go above root, if given.
   */
  Indigo.dom.rangeToTarget = function(range, root) {
    var anchor = range.commonAncestorContainer,
        target = {selectors: []},
        selector;

    anchor = $(anchor).closest('[id]')[0];
    if (root && anchor !== root &&
      (anchor.compareDocumentPosition(root) & Node.DOCUMENT_POSITION_CONTAINS) === 0) return;
    target.anchor_id = anchor.id;

    Indigo.dom.withoutForeignElements(anchor, function() {
      // position selector
      selector = textPositionFromRange(anchor, range);
      selector.type = "TextPositionSelector";
      target.selectors.push(selector);

      // quote selector, based on the position
      selector = textQuoteFromTextPosition(anchor, selector);
      selector.type = "TextQuoteSelector";
      target.selectors.push(selector);
    });

    return target;
  };

  /**
   * Convert a Target object (anchor_id, selectors) to Range object.
   *
   * This does its best to try to find a match, walking up the anchor hierarchy if possible.
   */
  Indigo.dom.targetToRange = function(target) {
    var anchor, range,
        anchor_id = target.anchor_id,
        ix = anchor_id.lastIndexOf('.');

    anchor = document.getElementById(anchor_id);

    if (!target.selectors) {
      // no selectors, old-style annotation for an entire element
      if (anchor) {
        range = document.createRange();
        range.selectNodeContents(anchor);
      }
      return range;
    }

    // do our best to find the anchor node, going upwards up the id chain if
    // the id has dotted components
    while (!anchor && ix > -1) {
      anchor_id = anchor_id.substring(0, ix);
      ix = anchor_id.lastIndexOf('.');
      anchor = document.getElementById(anchor_id);
    }

    if (!anchor) return;

    // remove foreign elements, then use the selectors to find the text
    // build up a Range object.
    return Indigo.dom.withoutForeignElements(anchor, function() {
      return Indigo.dom.selectorsToRange(anchor, target.selectors);
    });
  };

  /**
   * Given a root and a list of selectors, create browser Range object.
   *
   * Only TextPositionSelector and TextQuoteSelector types from https://www.w3.org/TR/annotation-model/
   * are used.
   */
  Indigo.dom.selectorsToRange = function(anchor, selectors) {
    var posnSelector = _.findWhere(selectors, {type: "TextPositionSelector"}),
      quoteSelector = _.findWhere(selectors, {type: "TextQuoteSelector"}),
      range;

    if (posnSelector) {
      range = Indigo.dom.textPositionToRange(anchor, posnSelector);

      // compare text with the exact from the quote selector
      if (quoteSelector && range.toString() === quoteSelector.exact) {
        return range;
      }
    }

    // fall back to the quote selector
    if (quoteSelector) {
      return Indigo.dom.textQuoteToRange(anchor, quoteSelector);
    }
  };

  /**
   * Mark all the text nodes in a range with a given tag (eg. 'mark'),
   * calling the callback for each new marked element.
   */
  Indigo.dom.markRange = function(range, tagName, callback) {
    var iterator, node, posn,
      nodes = [],
      start, end,
      ignore = {'TABLE': 1, 'THEAD': 1, 'TBODY': 1, 'TR': 1};

    function split(node, offset) {
      // split the text node so that the offsets fall on text node boundaries
      if (offset !== 0) {
        return node.splitText(offset);
      } else {
        return node;
      }
    }

    node = range.commonAncestorContainer;
    if (node.nodeType != Node.ELEMENT_NODE) node = node.parentElement;

    // remove foreign elements while working with the range
    Indigo.dom.withoutForeignElements(node, function() {
      if (range.startContainer.nodeType === Node.TEXT_NODE) {
        // split the start and end text nodes so that the offsets fall on text node boundaries
        start = split(range.startContainer, range.startOffset);
      } else {
        // first text node
        start = document.createNodeIterator(range.startContainer, NodeFilter.SHOW_TEXT).nextNode();
        if (!start) return;
      }

      if (range.endContainer.nodeType === Node.TEXT_NODE) {
        end = split(range.endContainer, range.endOffset);
      } else {
        end = range.endContainer;
      }

      // gather all the text nodes between start and end
      iterator = document.createNodeIterator(
        range.commonAncestorContainer, NodeFilter.SHOW_TEXT,
        function (n) {
          // ignore text nodes in weird positions in tables
          if (ignore[n.parentElement.tagName]) return NodeFilter.FILTER_SKIP;
          return NodeFilter.FILTER_ACCEPT;
        });

      // advance until we're at the start node
      node = iterator.nextNode();
      while (node && node !== start) node = iterator.nextNode();

      // gather text nodes
      while (node) {
        posn = node.compareDocumentPosition(end);
        // stop if node isn't inside end, and doesn't come before end
        if ((posn & Node.DOCUMENT_POSITION_CONTAINS) === 0 &&
          (posn & Node.DOCUMENT_POSITION_FOLLOWING) === 0) break;

        nodes.push(node);
        node = iterator.nextNode();
      }
    });

    // mark the gathered nodes
    nodes.forEach(function(node) {
      var mark = document.createElement(tagName || 'mark');
      node.parentElement.insertBefore(mark, node);
      mark.appendChild(node);
      if (callback) callback(mark);
    });
  };

  /**
   * Tweaked version of toRange from https://github.com/tilgovi/dom-anchor-text-position
   * so that we can fix a bug that arises when selecting to the end of a node.
   */
  Indigo.dom.textPositionToRange = function(root, selector) {
    if (root === undefined) {
      throw new Error('missing required parameter "root"');
    }

    var document = root.ownerDocument;
    var range = document.createRange();
    var iter = document.createNodeIterator(root, NodeFilter.SHOW_TEXT);

    var start = selector.start || 0;
    var end = selector.end || start;
    var count = domSeek(iter, start);
    var remainder = start - count;

    if (iter.pointerBeforeReferenceNode) {
      range.setStart(iter.referenceNode, remainder);
    } else {
      range.setStart(iter.nextNode(), remainder);
      iter.previousNode();
    }

    var length = end - start + remainder;
    count = domSeek(iter, length);
    remainder = length - count;

    if (iter.pointerBeforeReferenceNode) {
      range.setEnd(iter.referenceNode, remainder);
    } else {
      // XXX: work around a bug in dom-anchor-text-position, see
      // https://github.com/tilgovi/dom-anchor-text-position/issues/2
      var node = iter.nextNode();
      if (node) {
        range.setEnd(node, remainder);
      } else {
        range.setEnd(iter.referenceNode, iter.referenceNode.length);
      }
    }

    return range;
  };

  /**
   * Given a root and a TextQuoteSelector, convert it to a Range object.
   *
   * Re-implements toRange from https://github.com/tilgovi/dom-anchor-text-quote
   * so that we can call our custom textPositionToRange()
   */
  Indigo.dom.textQuoteToRange = function(root, selector, options) {
    return Indigo.dom.textPositionToRange(root, textQuoteToTextPosition(root, selector, options));
  };
});