<template>
  <div class="intertwine__email_capture">
    <input v-model="email_address" :placeholder="label">
    <button v-if="email_address" @click="validateEmail">Submit</button>
    <button v-if="!email_address" @click="shootBlank" disabled>Where to?</button>
    <p class="intertwine__email_capture--message">{{ message }}</p>
  </div>
</template>

<script>
export default {
  name: 'IntertwineHome',
  data () {
    return {
      label: 'Enter your email address to chart our progress...',
      email_address: null,
      message: null
    }
  },
  methods: {
    validateEmail (emailAddress) {
      return true
    },
    shootBlank () {
      return true
    }
  }
}
</script>

<style lang="scss" scoped >
.intertwine__email_capture {
  display: flex;
  padding: 0 2rem;

  input {
    padding: 1rem;
    width: 65%;
  }

  button {
    padding: 0 6rem;
  }
}

</style>
