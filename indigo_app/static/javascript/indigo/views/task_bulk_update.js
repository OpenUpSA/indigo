(function(exports) {
  "use strict";

  if (!exports.Indigo) exports.Indigo = {};
  Indigo = exports.Indigo;

  Indigo.TaskBulkUpdateView = Backbone.View.extend({
    el: '.page-body',
    events: {
      'change input[type=checkbox][name=tasks]': 'taskSelected',
    },

    initialize: function() {
      this.$form = this.$('#bulk-task-update-form');
      this.model = new Backbone.Model({'tasks': []});
      this.listenTo(this.model, 'change', this.updateFormOptions);
    },

    taskSelected: function(e) {
      var ids = _.map(document.querySelectorAll('input[type=checkbox][name=tasks]:checked'), function(e) { return e.value; });
      this.model.set('tasks', ids);

      $(e.target)
        .closest('.card-body')
        .toggleClass('bg-selected', e.checked);
    },

    updateFormOptions: function() {
      // assigned user options is the intersection of the assignment options for all tasks
      var options = null,
          names = {};

      // show the form?
      if (this.model.get('tasks').length > 0) {
        this.$form.siblings().addClass('d-none');
        this.$form.removeClass('d-none');
      } else {
        this.$form.siblings().removeClass('d-none');
        this.$form.addClass('d-none');
      }

      this.model.get('tasks').forEach(function(id) {
        var $buttons = $("#task-" + id + " .assign-task-form .dropdown-item[value]"),
            taskOptions = _.map($buttons, function(b) {
              names[b.value] = b.textContent;
              return b.value;
            });

        if (taskOptions.length > 0) {
          if (options === null) {
            options = taskOptions;
          } else {
            options = _.intersection(options, taskOptions);
          }
        }
      });

      var $select = this.$form.find('[name=assigned_to]').empty();
      var option = document.createElement('option');
      option.value = '-1';
      option.innerText = 'Unassign';
      $select.append(option);
      option = document.createElement('option');
      option.innerText = '-----';
      option.disabled = true;
      $select.append(option);

      options = _.sortBy(options || [], function(id) { return names[id]; });
      options.forEach(function (value) {
        var option = document.createElement('option');
        option.value = value;
        option.innerText = names[value];
        $select.append(option);
      });
    },
  });
})(window);
