<template>
  <main class="intertwine__problems stage">
    <h1>{{ headline }}</h1>
    <p>{{ blurb }}</p>

    <h2>Check out this stuff too</h2>

    <section class="intertwine__problems--browse" v-if="problems">
      <span v-for="(prob, index) in problems" :key="index">
        {{ prob.question }}
      </span>
    </section>
  </main>
</template>

<script>
import axios from 'axios'
export default {
  name: 'IntertwineProblems',
  data () {
    return {
      headline: 'Find a problem by Geo',
      blurb: 'Some blurb here about Problems by Geo',
      dataSource: 'http://0.0.0.0:5000/geos/?match_string=austin,%20tx&match_limit=-1',
      dataSource2: 'https://opentdb.com/api.php?amount=10',
      problems: [],
      error: null
    }
  },
  mounted () {
    this.makeCall()
  },
  methods: {
    makeCall () {
      let vm = this
      axios.get(this.dataSource)
        .then(function (response) {
          let responseData = response.data || {}
          let problemResults = responseData.results || []
          vm.problems = problemResults
        })
        .catch(function (error) {
          console.log(error)
        })
    }
  }
}
</script>

<style lang="scss" scoped>
@import "../sass/palette.scss";

.vue2leaflet-map {
  height: 5vh;
}

.intertwine__problems--browse {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: stretch;

  span {
    display: inline-block;
    padding: 2rem;
    background: rgba(white, .5);
    max-width: 15em;
    font-size: 1.5rem;
    transition: all .2s;
    color: rgba($light_blue, .8)

    &:hover {
      color: $light_blue;
      background: white;
      cursor: pointer;
    }
  }
}
</style>
