import Vue from 'vue'
import Router from 'vue-router'
import IntertwineHome from '@/components/intertwine_home'
import IntertwineCommunities from '@/components/intertwine_communities'
import IntertwineProblems from '@/components/intertwine_problems'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'IntertwineHome',
      component: IntertwineHome
    },
    {
      path: '/communities',
      name: 'IntertwineCommunities',
      component: IntertwineCommunities
    },
    {
      path: '/problems',
      name: 'IntertwineProblems',
      component: IntertwineProblems
    }
  ]
})
