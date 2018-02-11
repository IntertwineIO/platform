<template>
  <div class="intertwine__email_capture">
    <input v-model="email_address" :placeholder="label">
    <button v-if="email_address" @click="validateEmail">Submit</button>
    <button class="disabled" v-if="!email_address" @click="shootBlank" disabled>Your email?</button>
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
@import '~@/sass/palette.scss';

.intertwine__email_capture {
  display: flex;
  padding: 0 2rem;

  input {
    padding: 1rem;
    width: 65%;
    border: none;
    background: white;
    font-size: 1rem;
  }

  button {
    padding: 0 5rem;
    font-size: 1rem;
    background-color: $aqua;
    color: white;
    border: none;
  }

  .disabled {
    background-color: rgba(2,200,167,.5);
  }
}

</style>
