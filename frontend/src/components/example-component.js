// Example Alpine.js component
// This shows how to create reusable components

export function todoList() {
  return {
    todos: [],
    newTodo: '',
    
    addTodo() {
      if (this.newTodo.trim()) {
        this.todos.push({
          id: Date.now(),
          text: this.newTodo,
          completed: false
        })
        this.newTodo = ''
      }
    },
    
    toggleTodo(id) {
      const todo = this.todos.find(t => t.id === id)
      if (todo) {
        todo.completed = !todo.completed
      }
    },
    
    removeTodo(id) {
      this.todos = this.todos.filter(t => t.id !== id)
    }
  }
}

// Register the component globally
window.todoList = todoList