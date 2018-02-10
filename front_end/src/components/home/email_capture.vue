<template>
  <div id="intertwine__email_capture">
    <input v-model="email_address" :placeholder="label">
    <button v-show="email_address" @click="validateEmail">Submit</button>
  </div>
</template>

<script>
export default {
  name: 'IntertwineHome',
  data () {
    return {
      label: 'Enter your email address to chart our progress!',
      email_address: null
    }
  }
}
</script>
